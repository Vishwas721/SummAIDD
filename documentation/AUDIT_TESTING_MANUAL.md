# Epic 4.1 Audit Logging - Manual Testing Guide

## Overview
This document provides step-by-step instructions for manually testing the WORM (Write-Once-Read-Many) audit logging system implemented in Epic 4.1 Tasks 1-3.

## Prerequisites
1. Backend server running: `cd backend && python -m uvicorn main:app --reload --port 8000`
2. Frontend dev server running: `cd frontend && npm run dev`
3. PostgreSQL database initialized with audit_logs and alert_overrides tables
4. Browser DevTools Console open (F12) to monitor audit logger output

## Test Scenarios

### Test 1: VIEWED_SUMMARY Event (PatientChartView Mount)
**Trigger:** Doctor opens patient chart

**Steps:**
1. Log in as DOCTOR role (or ensure userRole = 'DOCTOR')
2. Navigate to `/patient/:patientId` (e.g., `/patient/80085`)
3. Wait for chart to fully load

**Expected Behavior:**
- Console message: `[AuditLogger] ✅ Audit logged: VIEWED_SUMMARY for patient XXXXX (log_id: N)`
- No UI freezing or loading spinners
- Chart renders normally

**Database Verification:**
```sql
SELECT 
  log_id, 
  patient_id, 
  user_id, 
  action_type, 
  action_metadata,
  created_at
FROM audit_logs 
WHERE action_type = 'VIEWED_SUMMARY' 
  AND patient_id = '80085'
ORDER BY created_at DESC 
LIMIT 1;
```

**Expected Result:**
- `action_type` = 'VIEWED_SUMMARY'
- `action_metadata` = `{"user_role": "DOCTOR", "timestamp": "ISO8601_string"}`
- `created_at` is timestamptz with timezone offset

---

### Test 2: CLICKED_CITATION Event (SummaryGrid Citation Click)
**Trigger:** Click "View Source" button on any summary card citation

**Steps:**
1. Navigate to patient chart with summaries loaded
2. Find a card with citations (e.g., Oncology Summary, Speech Summary)
3. Click the citation link or "View Source" button

**Expected Behavior:**
- Console message: `[AuditLogger] ✅ Audit logged: CLICKED_CITATION for patient XXXXX (log_id: N)`
- PDF viewer opens showing the source document
- No modal lag or stutter

**Database Verification:**
```sql
SELECT 
  log_id, 
  action_metadata->>'report_id' AS report_id,
  action_metadata->>'report_name' AS report_name,
  action_metadata->>'page' AS page,
  action_metadata->>'chunk_id' AS chunk_id
FROM audit_logs 
WHERE action_type = 'CLICKED_CITATION' 
  AND patient_id = '80085'
ORDER BY created_at DESC 
LIMIT 1;
```

**Expected Result:**
- `action_metadata` contains: `report_id`, `report_name`, `page`, `chunk_id`, `user_role`, `timestamp`
- All JSON fields are validly structured

---

### Test 3: CLICKED_CITATION Event (SummaryPanel Insurance Tab)
**Trigger:** Click citation in Insurance/TPA workflow tab

**Steps:**
1. Navigate to patient chart
2. Switch to "Insurance" or "TPA" tab
3. Click any citation link in the structured summary

**Expected Behavior:**
- Console message: `[AuditLogger] ✅ Audit logged: CLICKED_CITATION for patient XXXXX (log_id: N)`
- PDF viewer opens in side panel
- Full metadata captured (report_id, page, chunk_id)

**Database Verification:**
Same SQL as Test 2

---

### Test 4: EXPORTED_PDF Event (Prescription Download)
**Trigger:** Generate and download prescription PDF

**Steps:**
1. Navigate to patient chart
2. Expand "Write Prescription" section
3. Enter drug name (e.g., "Aspirin 81mg")
4. Click "Print Prescription" button

**Expected Behavior:**
- Console message: `[AuditLogger] ✅ Audit logged: EXPORTED_PDF for patient XXXXX (log_id: N)`
- jsPDF generates prescription PDF
- Download initiates immediately after audit log

**Database Verification:**
```sql
SELECT 
  log_id,
  action_metadata->>'document_type' AS document_type,
  action_metadata->>'user_role' AS user_role
FROM audit_logs 
WHERE action_type = 'EXPORTED_PDF' 
  AND patient_id = '80085'
  AND action_metadata->>'document_type' = 'prescription'
ORDER BY created_at DESC 
LIMIT 1;
```

**Expected Result:**
- `action_metadata.document_type` = 'prescription'

---

### Test 5: EXPORTED_PDF Event (Clinical Summary - PatientChartView)
**Trigger:** Download clinical summary from main chart view

**Steps:**
1. Navigate to patient chart
2. Scroll to bottom of summary section
3. Click "Download Clinical Summary" button

**Expected Behavior:**
- Console message: `[AuditLogger] ✅ Audit logged: EXPORTED_PDF for patient XXXXX (log_id: N)`
- PDF downloads with formatted clinical summary

**Database Verification:**
```sql
SELECT 
  log_id,
  action_metadata->>'document_type' AS document_type
FROM audit_logs 
WHERE action_type = 'EXPORTED_PDF' 
  AND patient_id = '80085'
  AND action_metadata->>'document_type' = 'clinical_summary'
ORDER BY created_at DESC 
LIMIT 1;
```

---

### Test 6: EXPORTED_PDF Event (Clinical Summary - SummaryGrid)
**Trigger:** Export AI-generated summary from card layout

**Steps:**
1. Navigate to patient chart
2. Find the "Export Summary PDF" button in SummaryGrid component
3. Click to generate PDF

**Expected Behavior:**
- Console message: `[AuditLogger] ✅ Audit logged: EXPORTED_PDF for patient XXXXX (log_id: N)`
- jsPDF generates card-based summary layout

**Database Verification:**
Same SQL as Test 5

---

### Test 7: Silent Failure Handling (Backend Offline)
**Trigger:** Stop backend server while frontend is running

**Steps:**
1. Stop backend server: `Ctrl+C` in uvicorn terminal
2. In browser, navigate to new patient chart
3. Check browser console

**Expected Behavior:**
- Console warning: `[AuditLogger] ⚠️ Failed to log audit event: VIEWED_SUMMARY - Error: fetch failed`
- UI continues to render normally
- **NO popup alerts, error modals, or crashes**
- Chart loads all other data (assuming backend restarts or uses cached data)

**Database Verification:**
No new audit_logs entries created (expected)

---

### Test 8: Invalid Input Validation
**Trigger:** Call audit logger with missing/invalid parameters

**Steps (execute in browser console):**
```javascript
// Import the logger
import { logAudit } from '/src/utils/auditLogger.js'

// Test missing patientId
logAudit(null, 'VIEWED_SUMMARY', {})  
// Expected: console.error "patientId is required"

// Test missing actionType
logAudit('12345', null, {})  
// Expected: console.error "actionType is required"

// Test invalid actionType
logAudit('12345', 'INVALID_ACTION', {})  
// Expected: console.error "Invalid action type"
```

**Expected Behavior:**
- Each invalid call logs descriptive error to console
- No network requests sent for invalid inputs
- No exceptions thrown (silent validation failure)

---

### Test 9: UI Non-Blocking Verification (Network Throttling)
**Trigger:** Slow network + rapid UI interactions

**Steps:**
1. Open Chrome DevTools → Network Tab
2. Set throttling to "Slow 3G"
3. Navigate to patient chart
4. Immediately start clicking citations, export buttons rapidly

**Expected Behavior:**
- UI remains responsive during audit logging
- No "waiting for localhost:8000" spinners
- All interactions execute without blocking
- Audit logs appear in console with slight delay (~2-5 seconds)

**Database Verification (after network throttling disabled):**
```sql
SELECT 
  action_type, 
  COUNT(*) 
FROM audit_logs 
WHERE patient_id = '80085' 
  AND created_at > NOW() - INTERVAL '5 minutes'
GROUP BY action_type;
```

**Expected Result:**
All audit events eventually logged (may be delayed but none dropped)

---

## Acceptance Criteria Checklist

### Epic 4.1 Task 1: Database Schema
- [ ] `audit_logs` table exists with all columns (log_id, patient_id, user_id, action_type, action_metadata, created_at)
- [ ] `alert_overrides` table exists with WORM compliance
- [ ] All `created_at` columns use TIMESTAMPTZ (not TIMESTAMP)
- [ ] FK constraint `patient_id REFERENCES patients(patient_id)` works (not patients(id))
- [ ] CHECK constraint enforces valid `action_type` enum values
- [ ] Pydantic `AuditActionType` enum exported in `schemas.py`

### Epic 4.1 Task 2: Backend Endpoints
- [ ] POST /audit/log endpoint registered and accepts AuditLogCreate
- [ ] GET /audit/{patient_id} returns List[AuditLogResponse] chronologically
- [ ] POST /audit/safety-check/override creates both alert_overrides + audit_logs entries
- [ ] All endpoints use synchronous `def` (not `async def`) for psycopg2 compatibility
- [ ] `json.dumps()` used for all dict→JSONB conversions
- [ ] NO UPDATE or DELETE routes exist for audit tables (WORM principle)
- [ ] Swagger UI documents all 3 endpoints at http://localhost:8000/docs

### Epic 4.1 Task 3: Frontend Integration
- [ ] `auditLogger.js` utility created with `logAudit()` core function
- [ ] AUDIT_ACTIONS constants match backend AuditActionType enum
- [ ] Helper functions created: logViewedSummary, logClickedCitation, logExportedPdf
- [ ] PatientChartView logs VIEWED_SUMMARY on mount (DOCTOR role only)
- [ ] PatientChartView logs EXPORTED_PDF for prescriptions
- [ ] PatientChartView logs EXPORTED_PDF for clinical summary download
- [ ] SummaryGrid logs CLICKED_CITATION on citation clicks
- [ ] SummaryGrid logs EXPORTED_PDF on summary export
- [ ] SummaryPanel logs CLICKED_CITATION on Insurance tab citations
- [ ] All audit calls are non-blocking (async, fire-and-forget)
- [ ] Silent failure handling: console warnings only, no UI crashes
- [ ] Auto-enrichment: user_id, user_role, timestamp added to all events

---

## Troubleshooting

### Issue: No console messages appear
**Solution:** Check browser console filter is set to "All levels" (not just Errors)

### Issue: "fetch failed" errors
**Solution:** Verify backend server is running on http://localhost:8000

### Issue: Database queries return 0 rows
**Solution:** 
1. Check migrations applied: `SELECT * FROM audit_logs LIMIT 1;`
2. Verify backend logged the request: check uvicorn console logs
3. Confirm patient_id matches: frontend uses string, backend expects TEXT

### Issue: JSONB columns show null
**Solution:** Ensure backend uses `json.dumps(metadata)` before INSERT (line 64 in audit_router.py)

### Issue: TypeError "dict is not serializable"
**Solution:** Backend must use `json.dumps()` wrapper for JSONB fields (not raw Python dicts)

---

## Performance Benchmarks

### Expected Response Times (Local Development)
- POST /audit/log: < 100ms
- GET /audit/{patient_id}: < 200ms (for ~100 logs)
- Frontend audit call: < 10ms (non-blocking dispatch)

### Expected UI Impact
- VIEWED_SUMMARY logging: 0ms perceived delay
- CLICKED_CITATION logging: 0ms perceived delay
- EXPORTED_PDF logging: 0ms perceived delay

### Database Growth Estimates
- Per patient chart view: 1 audit_logs row (~500 bytes)
- Per citation click: 1 audit_logs row (~800 bytes with metadata)
- Per PDF export: 1 audit_logs row (~600 bytes)
- **Daily estimate (100 patients, 5 actions each):** 500 rows/day = ~350 KB/day

---

## Next Steps After Testing
1. Monitor production logs for silent failures
2. Set up database archival policy (audit_logs retention > 7 years for HIPAA)
3. Create analytics dashboard for action_type frequency
4. Implement alert_overrides UI workflow (Epic 4.1 Task 4)
5. Add PRESCRIBED_DRUG audit logging (Epic 4.2)

---

**Last Updated:** 2025-01-XX  
**Epic:** 4.1 WORM Audit Logging  
**Tasks Covered:** 1 (Schema), 2 (Backend), 3 (Frontend)
