/**
 * Audit Logger Utility (Epic 4.1)
 * Silent background logging for WORM-compliant healthcare audit trail
 * 
 * Features:
 * - Asynchronous, non-blocking audit event tracking
 * - Silent failures (console warnings only, no UI disruption)
 * - Minimal overhead for UI performance
 * 
 * Usage:
 * import { logAudit } from '@/utils/auditLogger'
 * 
 * logAudit(patientId, 'VIEWED_SUMMARY', { session_id: '...' })
 * logAudit(patientId, 'CLICKED_CITATION', { citation_id: 42, page: 3 })
 * logAudit(patientId, 'EXPORTED_PDF', { filename: 'prescription.pdf' })
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Valid audit action types (must match backend AuditActionType enum)
 */
export const AUDIT_ACTIONS = {
  VIEWED_SUMMARY: 'VIEWED_SUMMARY',
  CLICKED_CITATION: 'CLICKED_CITATION',
  PRESCRIBED_DRUG: 'PRESCRIBED_DRUG',
  EXPORTED_PDF: 'EXPORTED_PDF',
  OVERRODE_ALERT: 'OVERRODE_ALERT',
}

/**
 * Log an audit event to the backend
 * 
 * @param {number} patientId - Patient ID
 * @param {string} actionType - Action type from AUDIT_ACTIONS
 * @param {object} metadata - Optional metadata for the action
 * @returns {Promise<void>} Resolves silently, logs errors to console
 * 
 * @example
 * // Log when doctor views patient summary
 * logAudit(123, AUDIT_ACTIONS.VIEWED_SUMMARY, { 
 *   timestamp: Date.now(), 
 *   user_agent: navigator.userAgent 
 * })
 * 
 * @example
 * // Log when citation is clicked
 * logAudit(123, AUDIT_ACTIONS.CLICKED_CITATION, {
 *   citation_id: 42,
 *   report_id: 5,
 *   page_number: 3
 * })
 */
export async function logAudit(patientId, actionType, metadata = null) {
  const normalizedPatientId = normalizePatientId(patientId)

  // Skip if patient ID is invalid
  if (normalizedPatientId === null) {
    console.warn('[AuditLogger] Invalid patient ID, skipping audit log:', patientId)
    return
  }

  // Skip if action type is invalid
  if (!Object.values(AUDIT_ACTIONS).includes(actionType)) {
    console.warn('[AuditLogger] Invalid action type, skipping audit log:', actionType)
    return
  }

  // Get current user from localStorage (assuming authentication context)
  const userId = localStorage.getItem('username') || 'unknown_user'
  const userRole = localStorage.getItem('user_role') || 'UNKNOWN'

  const payload = {
    patient_id: normalizedPatientId,
    user_id: userId,
    action_type: actionType,
    action_metadata: metadata ? {
      ...metadata,
      user_role: userRole,
      timestamp: new Date().toISOString(),
    } : null,
  }

  try {
    const response = await fetch(`${API_BASE_URL}/audit/log`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.warn('[AuditLogger] Failed to log audit event:', response.status, errorText)
      return
    }

    const result = await response.json()
    console.debug('[AuditLogger] ✅ Audit logged:', actionType, 'log_id:', result.log_id)
  } catch (error) {
    // Silent failure - only log to console, do not throw
    console.warn('[AuditLogger] Network error logging audit event:', error.message)
  }
}

/**
 * Helper to log viewed summary action
 * @param {number} patientId - Patient ID
 */
export function logViewedSummary(patientId) {
  return logAudit(patientId, AUDIT_ACTIONS.VIEWED_SUMMARY, {
    source: 'PatientChartView',
    user_agent: navigator.userAgent,
  })
}

/**
 * Helper to log citation click action
 * @param {number} patientId - Patient ID
 * @param {object} citationData - Citation metadata (report_id, page, chunk_id, etc.)
 */
export function logClickedCitation(patientId, citationData = {}) {
  return logAudit(patientId, AUDIT_ACTIONS.CLICKED_CITATION, {
    citation_id: citationData.source_chunk_id || citationData.chunk_id,
    report_id: citationData.report_id,
    page_number: citationData.source_metadata?.page || citationData.source_metadata?.page_number,
    report_name: citationData.report_name,
  })
}

/**
 * Helper to log PDF export action
 * @param {number} patientId - Patient ID
 * @param {string} exportType - Type of export ('prescription', 'summary', etc.)
 */
export function logExportedPdf(patientId, exportType = 'unknown') {
  return logAudit(patientId, AUDIT_ACTIONS.EXPORTED_PDF, {
    export_type: exportType,
    filename: `${exportType}_patient_${patientId}_${Date.now()}.pdf`,
  })
}

/**
 * Helper to log drug prescription action
 * @param {number} patientId - Patient ID
 * @param {object} prescriptionData - Drug details (drug_name, dosage, etc.)
 */
export function logPrescribedDrug(patientId, prescriptionData = {}) {
  return logAudit(patientId, AUDIT_ACTIONS.PRESCRIBED_DRUG, {
    drug_name: prescriptionData.drug_name,
    dosage: prescriptionData.dosage,
    frequency: prescriptionData.frequency,
    duration: prescriptionData.duration,
  })
}

export default logAudit

/**
 * Normalize patientId values coming from route params (often strings)
 * into a strict integer format expected by audit logging.
 *
 * @param {number|string} patientId
 * @returns {number|null}
 */
function normalizePatientId(patientId) {
  if (typeof patientId === 'number') {
    return Number.isInteger(patientId) && patientId > 0 ? patientId : null
  }

  if (typeof patientId === 'string') {
    const trimmed = patientId.trim()
    if (!/^\d+$/.test(trimmed)) return null

    const parsed = Number.parseInt(trimmed, 10)
    return Number.isInteger(parsed) && parsed > 0 ? parsed : null
  }

  return null
}
