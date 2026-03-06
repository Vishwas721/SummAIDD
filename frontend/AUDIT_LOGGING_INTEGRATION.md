# Frontend Audit Logging Integration Guide

## Overview
Epic 4.1 implements WORM (Write Once, Read Many) audit logging to track all doctor interactions with patient charts for healthcare compliance.

## Architecture

### Utility Module
**Location:** `frontend/src/utils/auditLogger.js`

**Key Functions:**
- `logAudit(patientId, actionType, metadata)` - Core logging function
- `logViewedSummary(patientId)` - Helper for VIEWED_SUMMARY events
- `logClickedCitation(patientId, citationData)` - Helper for CLICKED_CITATION events
- `logExportedPdf(patientId, exportType)` - Helper for EXPORTED_PDF events
- `logPrescribedDrug(patientId, prescriptionData)` - Helper for PRESCRIBED_DRUG events

**Features:**
- ✅ Asynchronous, non-blocking execution
- ✅ Silent failure (console warnings only, no UI disruption)
- ✅ Automatic metadata enrichment (user_role, timestamp)
- ✅ Input validation (patient ID, action type)

## Integration Points

### 1. VIEWED_SUMMARY
**Component:** `PatientChartView.jsx`
**Trigger:** When doctor opens patient chart (component mount)
**Code:**
```javascript
useEffect(() => {
  if (!patientId || userRole !== 'DOCTOR') return
  logViewedSummary(patientId)
}, [patientId, userRole])
```

### 2. CLICKED_CITATION
**Components:** 
- `SummaryGrid.jsx` → `openCitation()`
- `SummaryPanel.jsx` → `handleOpenCitation()`

**Trigger:** When doctor clicks citation link/number
**Code:**
```javascript
const openCitation = async (citation) => {
  logClickedCitation(patientId, citation)
  // ... rest of citation handling
}
```

### 3. EXPORTED_PDF
**Components:**
- `PatientChartView.jsx` → `handlePrintPrescription()` (prescription PDF)
- `PatientChartView.jsx` → `handleDownloadPdf()` (clinical summary PDF)
- `SummaryGrid.jsx` → Export button onClick (clinical summary PDF)

**Trigger:** When doctor exports PDF documents
**Code:**
```javascript
const handlePrintPrescription = () => {
  logExportedPdf(patientId, 'prescription')
  // ... PDF generation
}
```

## Audit Event Types

| Action Type | Description | Metadata Examples |
|------------|-------------|-------------------|
| `VIEWED_SUMMARY` | Doctor opened patient chart | `{ source, user_agent, session_id }` |
| `CLICKED_CITATION` | Doctor clicked citation link | `{ citation_id, report_id, page_number }` |
| `PRESCRIBED_DRUG` | Doctor prescribed medication | `{ drug_name, dosage, frequency }` |
| `EXPORTED_PDF` | Doctor exported PDF | `{ export_type, filename }` |
| `OVERRODE_ALERT` | Doctor overrode allergy alert | Auto-logged by backend |

## Error Handling

### Silent Failures
All audit logging failures are handled gracefully:
```javascript
try {
  const response = await fetch('/audit/log', { ... })
  if (!response.ok) {
    console.warn('[AuditLogger] Failed to log audit event:', response.status)
    return // Silent failure, no throw
  }
} catch (error) {
  console.warn('[AuditLogger] Network error logging audit event:', error.message)
  // No throw - UI continues normally
}
```

### Validation
Invalid inputs are detected early:
```javascript
if (!patientId || typeof patientId !== 'number') {
  console.warn('[AuditLogger] Invalid patient ID, skipping audit log')
  return
}
```

## Performance Considerations

1. **Non-blocking**: All audit calls use async/await without blocking UI rendering
2. **Fire-and-forget**: No UI waits for audit responses
3. **Minimal overhead**: ~50-100ms network request (non-blocking)
4. **No retries**: Failed audits are logged to console but not retried

## Testing Checklist

- [ ] VIEWED_SUMMARY logged when doctor opens patient chart
- [ ] CLICKED_CITATION logged when citation clicked
- [ ] EXPORTED_PDF logged for prescription export
- [ ] EXPORTED_PDF logged for clinical summary export
- [ ] UI works normally when backend is down (silent failure)
- [ ] No UI lag or blocking when audit logs are sent
- [ ] Console shows audit success messages in debug mode
- [ ] Database receives audit entries with correct metadata

## Adding New Audit Points

To add audit logging to a new action:

1. Import the logger:
```javascript
import { logAudit, AUDIT_ACTIONS } from '../utils/auditLogger'
```

2. Call at the appropriate point:
```javascript
const handleNewAction = () => {
  logAudit(patientId, AUDIT_ACTIONS.YOUR_ACTION_TYPE, {
    custom_field: 'value',
    timestamp: Date.now()
  })
  // ... rest of action handling
}
```

3. Test silent failure by stopping backend
4. Verify no UI disruption

## Backend API

**Endpoint:** `POST /audit/log`

**Request:**
```json
{
  "patient_id": 1,
  "user_id": "dr_smith",
  "action_type": "VIEWED_SUMMARY",
  "action_metadata": {
    "source": "PatientChartView",
    "user_role": "DOCTOR",
    "timestamp": "2026-03-07T10:30:00.000Z"
  }
}
```

**Response (201 Created):**
```json
{
  "log_id": 42,
  "patient_id": 1,
  "user_id": "dr_smith",
  "action_type": "VIEWED_SUMMARY",
  "action_metadata": { ... },
  "created_at": "2026-03-07T10:30:00.123456+00:00"
}
```

## Troubleshooting

### Audit logs not appearing in database
1. Check browser console for warnings
2. Verify backend server is running
3. Check Network tab for failed requests
4. Verify user is logged in (localStorage.getItem('username'))
5. Ensure patient ID is valid number

### UI freezing or lagging
1. Ensure audit calls are NOT awaited in render path
2. Verify async/await is used correctly
3. Check for accidental blocking in event handlers

### Console warnings about invalid action types
1. Verify action type matches backend enum exactly
2. Use constants from `AUDIT_ACTIONS` object
3. Check for typos in action type strings
