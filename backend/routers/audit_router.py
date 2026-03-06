"""
Audit & Alert Override Router (Epic 4.1 & 4.2)
WORM-Compliant Logging for Healthcare Compliance

Implements immutable audit trail for doctor interactions and allergy alert overrides.
NO UPDATE or DELETE operations permitted - Write Once, Read Many (WORM) principle.
"""

import json
import logging
from typing import List
from fastapi import APIRouter, HTTPException, status
from database import get_db_connection
from schemas import (
    AuditLogCreate,
    AuditLogResponse,
    AlertOverrideCreate,
    AlertOverrideResponse,
    AuditActionType,
)

router = APIRouter(prefix="/audit", tags=["Audit & Compliance"])
logger = logging.getLogger(__name__)


# ============================================================================
# AUDIT LOG ENDPOINTS
# ============================================================================

@router.post("/log", response_model=AuditLogResponse, status_code=status.HTTP_201_CREATED)
def create_audit_log(payload: AuditLogCreate):
    """
    Create a new audit log entry (WORM - Write Once, Read Many).
    
    Records doctor interactions with patient charts for compliance tracking.
    This endpoint is fire-and-forget for UI performance.
    
    **Action Types:**
    - VIEWED_SUMMARY: Doctor opened patient summary
    - CLICKED_CITATION: Doctor clicked a citation link
    - PRESCRIBED_DRUG: Doctor prescribed medication
    - EXPORTED_PDF: Doctor exported patient data
    - OVERRODE_ALERT: Doctor overrode an allergy alert (auto-logged via /safety-check/override)
    
    **Example Metadata:**
    ```json
    {
        "citation_id": 42,
        "drug_name": "Lisinopril",
        "dosage": "10mg",
        "pdf_url": "https://..."
    }
    ```
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Insert audit log with TIMESTAMPTZ
        cur.execute(
            """
            INSERT INTO audit_logs 
                (patient_id, user_id, action_type, action_metadata, created_at)
            VALUES (%s, %s, %s, %s, NOW())
            RETURNING log_id, patient_id, user_id, action_type, action_metadata, created_at
            """,
            (
                payload.patient_id,
                payload.user_id,
                payload.action_type.value,  # Extract enum value
                json.dumps(payload.action_metadata) if payload.action_metadata else None,
            )
        )
        
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create audit log entry"
            )
        
        return AuditLogResponse(
            log_id=row[0],
            patient_id=row[1],
            user_id=row[2],
            action_type=AuditActionType(row[3]),  # Convert back to enum
            action_metadata=row[4],
            created_at=row[5],
        )
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        logger.error(f"Error creating audit log: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@router.get("/{patient_id}", response_model=List[AuditLogResponse])
def get_audit_logs(patient_id: int):
    """
    Retrieve chronological audit trail for a patient.
    
    Returns all audit events sorted by timestamp (oldest first).
    Useful for medico-legal exports and compliance reviews.
    
    **Use Cases:**
    - Generating audit reports for legal proceedings
    - Compliance reviews by hospital administration
    - Patient access requests (Right to Information)
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
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {patient_id} not found"
            )
        
        # Retrieve all audit logs in chronological order
        cur.execute(
            """
            SELECT log_id, patient_id, user_id, action_type, action_metadata, created_at
            FROM audit_logs
            WHERE patient_id = %s
            ORDER BY created_at ASC
            """,
            (patient_id,)
        )
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        return [
            AuditLogResponse(
                log_id=row[0],
                patient_id=row[1],
                user_id=row[2],
                action_type=AuditActionType(row[3]),
                action_metadata=row[4],
                created_at=row[5],
            )
            for row in rows
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Error retrieving audit logs for patient {patient_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


# ============================================================================
# ALERT OVERRIDE ENDPOINTS  
# ============================================================================

@router.post("/safety-check/override", response_model=AlertOverrideResponse, status_code=status.HTTP_201_CREATED)
def create_alert_override(payload: AlertOverrideCreate):
    """
    Record an allergy alert override with doctor justification.
    
    **Dual Action:**
    1. Inserts override record into `alert_overrides` table
    2. Automatically creates an audit log with `OVERRODE_ALERT` action type
    
    This endpoint enforces accountability when prescribing against known allergies.
    
    **Example Scenario:**
    Patient has "penicillin allergy" in medical history. Doctor prescribes Penicillin V
    after successful tolerance testing. Override captures:
    - Drug name: "Penicillin V"
    - Allergy keyword: "penicillin"
    - Justification: "Patient tolerance test completed successfully; informed consent documented"
    - Doctor: "dr_smith"
    
    **Compliance:**
    - Satisfies medico-legal requirements for informed consent documentation
    - Creates immutable audit trail for liability protection
    - Enables retrospective review of clinical decision-making
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Step 1: Insert alert override
        cur.execute(
            """
            INSERT INTO alert_overrides 
                (patient_id, drug_name, allergy_keyword, doctor_reason, overridden_by, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING override_id, patient_id, drug_name, allergy_keyword, doctor_reason, overridden_by, created_at
            """,
            (
                payload.patient_id,
                payload.drug_name,
                payload.allergy_keyword,
                payload.doctor_reason,
                payload.overridden_by,
            )
        )
        
        override_row = cur.fetchone()
        
        if not override_row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create alert override"
            )
        
        # Step 2: Auto-create audit log for override action
        audit_metadata = {
            "override_id": override_row[0],
            "drug_name": payload.drug_name,
            "allergy_keyword": payload.allergy_keyword,
            "reason": payload.doctor_reason,
        }
        
        cur.execute(
            """
            INSERT INTO audit_logs 
                (patient_id, user_id, action_type, action_metadata, created_at)
            VALUES (%s, %s, %s, %s, NOW())
            """,
            (
                payload.patient_id,
                payload.overridden_by,
                AuditActionType.OVERRODE_ALERT.value,
                json.dumps(audit_metadata),
            )
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
        return AlertOverrideResponse(
            override_id=override_row[0],
            patient_id=override_row[1],
            drug_name=override_row[2],
            allergy_keyword=override_row[3],
            doctor_reason=override_row[4],
            overridden_by=override_row[5],
            created_at=override_row[6],
        )
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        logger.error(f"Error creating alert override: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
