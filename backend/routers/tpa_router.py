"""
TPA (Third Party Administrator) Consent Management Router
Phase 1 - Foundation & Consent

Implements DPDP Act-compliant consent workflow before TPA document validation.
Endpoints handle consent requests, OTP verification, and status checks.
"""

import os
import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from database import get_db_connection
from schemas import PatientConsentCreate, PatientConsentResponse

router = APIRouter(prefix="/tpa", tags=["TPA Consent"])
logger = logging.getLogger(__name__)

# Encryption key for mobile number storage
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "").strip()


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


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/consent/{patient_id}", response_model=PatientConsentResponse)
async def request_consent(patient_id: int, body: ConsentRequestBody):
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
        HTTPException 400: Consent already exists
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
            "SELECT consent_id FROM patient_consents WHERE patient_id = %s",
            (patient_id,)
        )
        existing = cur.fetchone()
        if existing:
            cur.close()
            conn.close()
            raise HTTPException(
                status_code=400,
                detail=f"Consent request already exists for patient {patient_id}"
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
async def verify_consent(patient_id: int, body: OTPVerificationBody):
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
async def get_consent_status(patient_id: int):
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
