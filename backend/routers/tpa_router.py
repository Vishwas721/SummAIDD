"""
TPA (Third Party Administrator) Consent Management Router
Phase 1 - Foundation & Consent

Implements DPDP Act-compliant consent workflow before TPA document validation.
Endpoints handle consent requests, OTP verification, and status checks.
"""

import os
import io
import asyncio
import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, Field
from database import get_db_connection
from schemas import PatientConsentResponse
from db_utils import (
    create_claim_record,
    insert_claim_document_encrypted,
    update_claim_status,
)
from tpa_prompts import _validate_claim_document

router = APIRouter(prefix="/tpa", tags=["TPA Consent"])
logger = logging.getLogger(__name__)

# Encryption key for mobile number storage
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "").strip()

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
}
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ConsentRequestBody(BaseModel):
    """Request body for initiating consent"""
    mobile_number: str = Field(
        ...,
        description="Patient's mobile number for OTP verification",
        min_length=10,
        max_length=15
    )


class OTPVerificationBody(BaseModel):
    """Request body for OTP verification"""
    otp: str = Field(
        ...,
        description="OTP code sent to patient's mobile (mock for Phase 1)",
        min_length=4,
        max_length=6
    )


class ClaimUploadResponse(BaseModel):
    """Immediate response after claim upload acceptance."""
    claim_id: int = Field(..., description="Created insurance claim ID")
    status: str = Field(..., description="Frontend processing status")


# ============================================================================
# ENDPOINTS
# ============================================================================

def _normalize_extracted_text(text: str) -> str:
    """Normalize extracted PDF/OCR text for cleaner downstream validation."""
    if not text:
        return ""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(" ".join(line.split()) for line in normalized.split("\n"))
    return normalized.strip()


def _extract_text_from_pdf(data: bytes) -> str:
    """Extract text from PDF bytes using PyMuPDF."""
    import fitz

    doc = fitz.open(stream=data, filetype="pdf")
    pages = []
    for page_index in range(doc.page_count):
        page = doc.load_page(page_index)
        pages.append(page.get_text() or "")
    doc.close()
    return _normalize_extracted_text("\n\n".join(pages))


def _extract_text_from_image(data: bytes) -> str:
    """Extract text from image bytes using pytesseract OCR."""
    import pytesseract
    from PIL import Image

    img = Image.open(io.BytesIO(data))
    text = pytesseract.image_to_string(img) or ""
    return _normalize_extracted_text(text)


def _run_claim_document_ingestion_task(
    claim_id: int,
    filename: str,
    mime_type: str,
    file_bytes: bytes,
    is_pdf: bool,
) -> None:
    """
    Background ingestion + validation placeholder for Phase 2.

    Heavy OCR/PDF extraction is intentionally done here to keep upload endpoint responsive.
    """
    try:
        extracted_text = _extract_text_from_pdf(file_bytes) if is_pdf else _extract_text_from_image(file_bytes)

        if not extracted_text or len(extracted_text) < 20:
            update_claim_status(
                claim_id,
                "RED",
                ["Insufficient extractable text found in uploaded claim document"],
            )
            logger.warning(f"[TPA VALIDATION] claim_id={claim_id} flagged RED (insufficient text)")
            return

        insert_claim_document_encrypted(
            claim_id=claim_id,
            filename=filename,
            mime_type=mime_type,
            extracted_text=extracted_text,
        )

        # Run async traffic-light LLM validation in the background worker context.
        # Run synchronous traffic-light LLM validation in the background worker context.
        validation = _validate_claim_document(extracted_text)
        update_claim_status(claim_id, validation.status.value, validation.discrepancies)
        logger.info(f"[TPA VALIDATION] claim_id={claim_id} completed with {validation.status.value} status")
    except Exception as e:
        logger.exception(f"[TPA VALIDATION] background task failed for claim_id={claim_id}: {e}")
        try:
            update_claim_status(claim_id, "RED", [f"system_error: {str(e)}"])
        except Exception:
            logger.exception(f"[TPA VALIDATION] failed to set RED fallback for claim_id={claim_id}")


def _patient_has_verified_consent(patient_id: int) -> bool:
    """Return True only when patient has a verified consent record."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT consent_status
            FROM patient_consents
            WHERE patient_id = %s
            ORDER BY requested_at DESC, consent_id DESC
            LIMIT 1
            """,
            (patient_id,),
        )
        row = cur.fetchone()
        cur.close()
        return bool(row and row[0] is True)
    finally:
        if conn:
            conn.close()


@router.post("/upload/{patient_id}", response_model=ClaimUploadResponse)
def upload_claim_document(
    patient_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Insurance claim document (PDF/JPG/PNG)"),
):
    """
    Ingest an insurance claim document, encrypt extracted text at rest, and trigger async validation.

    Returns immediately with claim_id while validation proceeds in a background task.
    """
    filename = file.filename or "uploaded_claim_document"
    suffix = os.path.splitext(filename)[1].lower()
    content_type = (file.content_type or "").lower()

    if content_type not in ALLOWED_CONTENT_TYPES and suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF, JPG, JPEG, or PNG files are allowed")

    if not _patient_has_verified_consent(patient_id):
        raise HTTPException(
            status_code=403,
            detail="Patient consent is required before uploading claim documents",
        )

    try:
        file_bytes = file.file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        is_pdf = content_type == "application/pdf" or suffix == ".pdf"
        mime = content_type or "application/octet-stream"

        # Parent claim row is created first, then heavy extraction + child insert run in background.
        claim_id = create_claim_record(patient_id=patient_id, status="PROCESSING", discrepancies=[])

        background_tasks.add_task(
            _run_claim_document_ingestion_task,
            claim_id,
            filename,
            mime,
            file_bytes,
            is_pdf,
        )

        return ClaimUploadResponse(claim_id=claim_id, status="PROCESSING")
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error uploading claim document for patient {patient_id}")
        raise HTTPException(status_code=500, detail=f"Claim upload failed: {e}")

@router.post("/consent/{patient_id}", response_model=PatientConsentResponse)
def request_consent(patient_id: int, body: ConsentRequestBody):
    """
    Initiate DPDP consent request for a patient.
    
    Creates a pending consent record and simulates sending OTP/SMS.
    Mobile number is encrypted before storage for privacy compliance.
    
    Args:
        patient_id: Patient ID requiring consent
        body: Contains mobile_number for OTP delivery
        
    Returns:
        PatientConsentResponse with pending consent status
        
    Raises:
        HTTPException 404: Patient not found
        HTTPException 400: Consent already verified
        HTTPException 500: Database error
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verify patient exists
        cur.execute("SELECT patient_id FROM patients WHERE patient_id = %s", (patient_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            raise HTTPException(
                status_code=404,
                detail=f"Patient with ID {patient_id} not found"
            )
        
        # Check if consent already exists
        cur.execute(
            """
            SELECT consent_id, consent_status
            FROM patient_consents
            WHERE patient_id = %s
            """,
            (patient_id,)
        )
        existing = cur.fetchone()

        # If consent already verified, block duplicate requests.
        if existing:
            consent_id, consent_status = existing

            if consent_status:
                cur.close()
                conn.close()
                raise HTTPException(
                    status_code=400,
                    detail=f"Consent already verified for patient {patient_id}"
                )

            # Existing pending consent: refresh request timestamps and mobile number,
            # then re-send mock OTP instead of locking user out.
            cur.execute(
                """
                UPDATE patient_consents
                SET mobile_number = pgp_sym_encrypt(%s, %s),
                    requested_at = CURRENT_TIMESTAMP,
                    responded_at = NULL,
                    consent_status = FALSE
                WHERE consent_id = %s
                RETURNING consent_id, patient_id, consent_status, requested_at, responded_at
                """,
                (body.mobile_number, ENCRYPTION_KEY, consent_id)
            )
            row = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()

            logger.info(
                f"[MOCK SMS] Re-sending OTP to {body.mobile_number[-4:].rjust(10, '*')} "
                f"for patient {patient_id}. Use any 4-6 digit code to verify."
            )

            return PatientConsentResponse(
                consent_id=row[0],
                patient_id=row[1],
                consent_status=row[2],
                requested_at=row[3],
                responded_at=row[4]
            )
        
        # Insert new consent request with encrypted mobile number
        cur.execute(
            """
            INSERT INTO patient_consents (patient_id, mobile_number, consent_status, requested_at)
            VALUES (%s, pgp_sym_encrypt(%s, %s), FALSE, CURRENT_TIMESTAMP)
            RETURNING consent_id, patient_id, consent_status, requested_at, responded_at
            """,
            (patient_id, body.mobile_number, ENCRYPTION_KEY)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        # Simulate OTP/SMS sending (Phase 1 mock)
        logger.info(
            f"[MOCK SMS] Sending OTP to {body.mobile_number[-4:].rjust(10, '*')} "
            f"for patient {patient_id}. Use any 4-6 digit code to verify."
        )
        
        return PatientConsentResponse(
            consent_id=row[0],
            patient_id=row[1],
            consent_status=row[2],
            requested_at=row[3],
            responded_at=row[4]
        )
        
    except HTTPException:
        if conn:
            conn.rollback()
            conn.close()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        logger.exception(f"Error requesting consent for patient {patient_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error while requesting consent: {str(e)}"
        )


@router.post("/consent/{patient_id}/verify", response_model=PatientConsentResponse)
def verify_consent(patient_id: int, body: OTPVerificationBody):
    """
    Verify OTP and grant consent for patient.
    
    Updates consent_status to TRUE after successful OTP validation.
    In Phase 1, accepts any 4-6 digit OTP (mock implementation).
    
    Args:
        patient_id: Patient ID to verify consent for
        body: Contains OTP code
        
    Returns:
        PatientConsentResponse with approved consent status
        
    Raises:
        HTTPException 404: Consent request not found
        HTTPException 400: Invalid OTP or already verified
        HTTPException 500: Database error
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get existing consent record
        cur.execute(
            """
            SELECT consent_id, consent_status 
            FROM patient_consents 
            WHERE patient_id = %s
            """,
            (patient_id,)
        )
        row = cur.fetchone()
        
        if not row:
            cur.close()
            conn.close()
            raise HTTPException(
                status_code=404,
                detail=f"No consent request found for patient {patient_id}"
            )
        
        consent_id, current_status = row
        
        if current_status:
            cur.close()
            conn.close()
            raise HTTPException(
                status_code=400,
                detail=f"Consent already verified for patient {patient_id}"
            )
        
        # Phase 1 Mock: Accept any 4-6 digit OTP
        if not body.otp.isdigit() or len(body.otp) < 4 or len(body.otp) > 6:
            cur.close()
            conn.close()
            logger.warning(f"Invalid OTP format for patient {patient_id}: {body.otp}")
            raise HTTPException(
                status_code=400,
                detail="Invalid OTP format. Must be 4-6 digits."
            )
        
        # Update consent status
        cur.execute(
            """
            UPDATE patient_consents 
            SET consent_status = TRUE, responded_at = CURRENT_TIMESTAMP
            WHERE patient_id = %s
            RETURNING consent_id, patient_id, consent_status, requested_at, responded_at
            """,
            (patient_id,)
        )
        updated_row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"[CONSENT GRANTED] Patient {patient_id} successfully verified OTP")
        
        return PatientConsentResponse(
            consent_id=updated_row[0],
            patient_id=updated_row[1],
            consent_status=updated_row[2],
            requested_at=updated_row[3],
            responded_at=updated_row[4]
        )
        
    except HTTPException:
        if conn:
            conn.rollback()
            conn.close()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        logger.exception(f"Error verifying consent for patient {patient_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error while verifying consent: {str(e)}"
        )


@router.get("/consent/{patient_id}", response_model=PatientConsentResponse)
def get_consent_status(patient_id: int):
    """
    Retrieve current consent status for a patient.
    
    Returns consent details without exposing encrypted mobile number.
    Used to check if patient has granted DPDP consent before TPA operations.
    
    Args:
        patient_id: Patient ID to check consent for
        
    Returns:
        PatientConsentResponse with current consent status
        
    Raises:
        HTTPException 404: Consent request not found
        HTTPException 500: Database error
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            SELECT consent_id, patient_id, consent_status, requested_at, responded_at
            FROM patient_consents
            WHERE patient_id = %s
            """,
            (patient_id,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"No consent record found for patient {patient_id}"
            )
        
        return PatientConsentResponse(
            consent_id=row[0],
            patient_id=row[1],
            consent_status=row[2],
            requested_at=row[3],
            responded_at=row[4]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.close()
        logger.exception(f"Error retrieving consent for patient {patient_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error while retrieving consent: {str(e)}"
        )
