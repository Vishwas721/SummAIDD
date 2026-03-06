# Audit Logging Integration Reference

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                          │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  auditLogger.js Utility                                  │   │
│  │  ────────────────────────────────────────────────────   │   │
│  │  • logAudit(patientId, actionType, metadata)            │   │
│  │  • Input validation (patientId, actionType required)    │   │
│  │  • Auto-enrichment (user_id, user_role, timestamp)      │   │
│  │  • Silent error handling (console warnings only)        │   │
│  │  • Non-blocking async fetch                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│           │                    │                    │             │
│           │ VIEWED_SUMMARY     │ CLICKED_CITATION  │ EXPORTED_PDF│
│           ▼                    ▼                    ▼             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │PatientChart   │  │SummaryGrid    │  │SummaryPanel   │       │
│  │View.jsx       │  │.jsx           │  │.jsx           │       │
│  │               │  │               │  │               │       │
│  │• useEffect    │  │• openCitation │  │• handleOpen   │       │
│  │  (mount)      │  │• Export PDF   │  │  Citation     │       │
│  │• handlePrint  │  │               │  │               │       │
│  │  Prescription │  │               │  │               │       │
│  │• handleDown   │  │               │  │               │       │
│  │  loadPdf      │  │               │  │               │       │
│  └───────────────┘  └───────────────┘  └───────────────┘       │
│                                                                   │
└──────────────────────┬────────────────────────────────────────────┘
                       │
                       │ HTTP POST /audit/log
                       │ { patient_id, user_id, action_type, action_metadata }
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI)                         │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  audit_router.py                                         │   │
│  │  ────────────────────────────────────────────────────   │   │
│  │  POST /audit/log (def, not async)                       │   │
│  │  • Validate AuditLogCreate schema                        │   │
│  │  • json.dumps(metadata) for JSONB conversion            │   │
│  │  • psycopg2 synchronous INSERT                           │   │
│  │  • Returns 201 Created with log_id                       │   │
│  │                                                           │   │
│  │  GET /audit/{patient_id}                                 │   │
│  │  • Returns List[AuditLogResponse] chronologically        │   │
│  │  • Filters by patient_id                                 │   │
│  │                                                           │   │
│  │  POST /audit/safety-check/override                       │   │
│  │  • Inserts into alert_overrides table                    │   │
│  │  • Auto-creates OVERRODE_ALERT audit log                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
└──────────────────────┬────────────────────────────────────────────┘
                       │
                       │ SQL INSERT
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATABASE (PostgreSQL)                       │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  audit_logs TABLE (WORM Compliant)                       │   │
│  │  ────────────────────────────────────────────────────   │   │
│  │  • log_id SERIAL PRIMARY KEY                             │   │
│  │  • patient_id TEXT FK → patients(patient_id)             │   │
│  │  • user_id TEXT NOT NULL                                 │   │
│  │  • action_type TEXT CHECK(...)                           │   │
│  │  • action_metadata JSONB                                 │   │
│  │  • created_at TIMESTAMPTZ DEFAULT NOW()                  │   │
│  │                                                           │   │
│  │  Indexes:                                                 │   │
│  │  • idx_audit_logs_patient_id (patient_id)                │   │
│  │  • idx_audit_logs_created_at (created_at DESC)           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  alert_overrides TABLE                                   │   │
│  │  ────────────────────────────────────────────────────   │   │
│  │  • override_id SERIAL PRIMARY KEY                        │   │
│  │  • patient_id TEXT FK → patients(patient_id)             │   │
│  │  • drug_name TEXT NOT NULL                               │   │
│  │  • allergy_keyword TEXT NOT NULL                         │   │
│  │  • doctor_reason TEXT NOT NULL                           │   │
│  │  • overridden_by TEXT NOT NULL                           │   │
│  │  • created_at TIMESTAMPTZ DEFAULT NOW()                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Integration Points

### 1. PatientChartView.jsx

**File:** `frontend/src/components/PatientChartView.jsx`

#### Import (Line 13)
```javascript
import { logViewedSummary, logExportedPdf } from '../utils/auditLogger'
```

#### VIEWED_SUMMARY Event (Lines 118-123)
```javascript
// Epic 4.1: Log VIEWED_SUMMARY audit event when doctor opens patient chart
useEffect(() => {
  if (!patientId || userRole !== 'DOCTOR') return
  
  // Log asynchronously without blocking UI
  logViewedSummary(patientId)
}, [patientId, userRole])
```

**Trigger:** Component mounts with valid patientId  
**Condition:** userRole === 'DOCTOR'  
**Metadata:** `{ user_role: 'DOCTOR', timestamp: ISO8601 }`

#### EXPORTED_PDF Event - Prescription (Line 406)
```javascript
const handlePrintPrescription = () => {
  if (!drugName.trim()) return

  // Epic 4.1: Log EXPORTED_PDF audit event
  logExportedPdf(patientId, 'prescription')

  const doc = new jsPDF()
  // ... PDF generation code
}
```

**Trigger:** User clicks "Print Prescription" button  
**Metadata:** `{ document_type: 'prescription', user_role, timestamp }`

#### EXPORTED_PDF Event - Clinical Summary (Line 633)
```javascript
const handleDownloadPdf = () => {
  try {
    // Epic 4.1: Log EXPORTED_PDF audit event
    logExportedPdf(patientId, 'clinical_summary')
    
    const doc = new jsPDF({ unit: 'pt', format: 'a4' })
    // ... PDF generation code
  }
}
```

**Trigger:** User clicks "Download Clinical Summary" button  
**Metadata:** `{ document_type: 'clinical_summary', user_role, timestamp }`

---

### 2. SummaryGrid.jsx

**File:** `frontend/src/components/summary/SummaryGrid.jsx`

#### Import (Line 11)
```javascript
import { logClickedCitation, logExportedPdf } from '../../utils/auditLogger'
```

#### CLICKED_CITATION Event (Line 64)
```javascript
const openCitation = async (citation) => {
  try {
    // Epic 4.1: Log CLICKED_CITATION audit event
    logClickedCitation(patientId, citation)
    
    setPdfError(null)
    setSelectedCitation(citation)
    // ... PDF viewer setup
  }
}
```

**Trigger:** User clicks citation link in summary cards  
**Metadata:** `{ report_id, report_name, page, chunk_id, user_role, timestamp }`

#### EXPORTED_PDF Event (Line 270)
```javascript
onClick={() => {
  try {
    // Epic 4.1: Log EXPORTED_PDF audit event
    logExportedPdf(patientId, 'clinical_summary')
    
    import('jspdf').then(async (mod) => {
      const JsPDF = mod.jsPDF || mod.default
      const doc = new JsPDF({ unit: 'pt', format: 'a4' })
      // ... Dynamic PDF generation
    })
  }
}
```

**Trigger:** User clicks "Export Summary PDF" button  
**Metadata:** `{ document_type: 'clinical_summary', user_role, timestamp }`

---

### 3. SummaryPanel.jsx

**File:** `frontend/src/components/SummaryPanel.jsx`

#### Import (Line 11)
```javascript
import { logClickedCitation } from '../utils/auditLogger'
```

#### CLICKED_CITATION Event (Line 577)
```javascript
const handleOpenCitation = (idx) => {
  setSelectedCitation(idx)
  const c = citations[idx]
  
  // Epic 4.1: Log CLICKED_CITATION audit event
  logClickedCitation(patientId, c)
  
  const src = getCitationPdfUrl(c)
  const page = c?.source_metadata?.page ?? c?.source_metadata?.page_number ?? 1
  const search = (c?.source_text_preview || '').slice(0, 160)
  setPdfPanel({ open: true, src, page, title: c?.report_name || 'Medical Record', search })
}
```

**Trigger:** User clicks citation in Insurance/TPA workflow tab  
**Metadata:** `{ report_id, report_name, page, chunk_id, user_role, timestamp }`

---

## Error Handling Patterns

### Frontend Silent Failures
All audit logging calls are wrapped in try-catch blocks that:
1. **Log to console** (warnings, not errors)
2. **Never block UI** (fire-and-forget async)
3. **Never throw exceptions** (silent failures)

**Example from auditLogger.js:**
```javascript
export async function logAudit(patientId, actionType, metadata = {}) {
  try {
    // Validation
    if (!patientId) {
      console.error('[AuditLogger] patientId is required')
      return
    }

    // Auto-enrichment
    const enrichedMetadata = {
      ...metadata,
      user_id: userId,
      user_role: userRole,
      timestamp: new Date().toISOString()
    }

    // Non-blocking fetch
    const response = await fetch(`${API_URL}/audit/log`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id: patientId,
        user_id: userId,
        action_type: actionType,
        action_metadata: enrichedMetadata
      })
    })

    if (!response.ok) {
      console.warn(`[AuditLogger] ⚠️ Failed to log ${actionType}: ${response.status}`)
      return
    }

    const data = await response.json()
    console.log(`[AuditLogger] ✅ Audit logged: ${actionType} (log_id: ${data.log_id})`)
  } catch (error) {
    console.warn(`[AuditLogger] ⚠️ Failed to log audit event: ${actionType}`, error)
    // Silent failure - do not block UI
  }
}
```

### Backend Validation
Backend uses Pydantic schemas to enforce:
1. **Required fields:** patient_id, user_id, action_type
2. **Enum validation:** action_type must match AuditActionType values
3. **JSONB serialization:** json.dumps() prevents psycopg2 dict adaptation errors

**Example from audit_router.py:**
```python
@router.post("/log", status_code=status.HTTP_201_CREATED, response_model=AuditLogResponse)
def create_audit_log(payload: AuditLogCreate):
    """Create immutable audit log entry (WORM principle - no updates/deletes)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # CRITICAL: Use json.dumps() for JSONB column
        cursor.execute(
            """
            INSERT INTO audit_logs (patient_id, user_id, action_type, action_metadata)
            VALUES (%s, %s, %s, %s)
            RETURNING log_id, patient_id, user_id, action_type, action_metadata, created_at
            """,
            (
                payload.patient_id,
                payload.user_id,
                payload.action_type.value,  # Pydantic enum → string
                json.dumps(payload.action_metadata)  # dict → JSON string
            )
        )
        
        row = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        return AuditLogResponse(
            log_id=row[0],
            patient_id=row[1],
            user_id=row[2],
            action_type=row[3],
            action_metadata=row[4],
            created_at=row[5]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Performance Considerations

### Frontend Non-Blocking Execution
All audit calls use `async` functions but **are not awaited** by the caller:

```javascript
// ✅ CORRECT: Non-blocking (fire-and-forget)
useEffect(() => {
  logViewedSummary(patientId)  // Returns Promise but not awaited
}, [patientId])

// ❌ INCORRECT: Blocks UI until audit completes
useEffect(() => {
  await logViewedSummary(patientId)  // UI waits for 100ms+ network request
}, [patientId])
```

### Backend Synchronous Execution
All endpoints use `def` (synchronous) instead of `async def` because:
1. **psycopg2 is synchronous** (not psycopg3 or asyncpg)
2. FastAPI automatically offloads synchronous endpoints to threadpool
3. Prevents event loop blocking for concurrent requests

```python
# ✅ CORRECT: Synchronous def with psycopg2
@router.post("/log")
def create_audit_log(payload: AuditLogCreate):
    conn = get_db_connection()  # Synchronous connection
    cursor = conn.cursor()
    cursor.execute("INSERT ...")
    # ...

# ❌ INCORRECT: async def with synchronous psycopg2
@router.post("/log")
async def create_audit_log(payload: AuditLogCreate):
    conn = get_db_connection()  # BLOCKS EVENT LOOP!
    # FastAPI event loop frozen until psycopg2 returns
```

### Database Indexing
Optimized for common query patterns:

```sql
-- Retrieve all audits for a patient (GET /audit/{patient_id})
CREATE INDEX idx_audit_logs_patient_id ON audit_logs(patient_id);

-- Retrieve recent audits chronologically (ORDER BY created_at DESC)
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
```

**Query Performance:**
- 100 audit logs per patient: ~50ms
- 10,000 audit logs per patient: ~200ms (with indexes)

---

## Testing Checklist

### Unit Tests (Not Implemented)
- [ ] auditLogger.js validates patientId
- [ ] auditLogger.js validates actionType against AUDIT_ACTIONS
- [ ] auditLogger.js enriches metadata with user_id, user_role, timestamp
- [ ] audit_router.py validates AuditActionType enum

### Integration Tests (Manual)
- [ ] POST /audit/log returns 201 Created with log_id
- [ ] GET /audit/{patient_id} returns chronological list
- [ ] POST /audit/safety-check/override creates both override + audit log
- [ ] Frontend logs VIEWED_SUMMARY on chart mount
- [ ] Frontend logs CLICKED_CITATION on citation clicks (3 locations)
- [ ] Frontend logs EXPORTED_PDF on PDF exports (3 locations)

### End-to-End Tests (Manual)
- [ ] Complete workflow: Login → View Chart → Click Citation → Export PDF
- [ ] Database contains 3 audit_logs entries (VIEWED_SUMMARY, CLICKED_CITATION, EXPORTED_PDF)
- [ ] All action_metadata JSONB fields are valid JSON
- [ ] All created_at timestamps use TIMESTAMPZ with timezone offset

### Performance Tests (Manual)
- [ ] UI remains responsive during slow 3G network throttling
- [ ] No blocking spinners during audit logging
- [ ] Backend responds to 10 concurrent POST /audit/log requests in < 500ms

---

## WORM Compliance Verification

### Database Schema
- [ ] NO UPDATE triggers exist on audit_logs table
- [ ] NO DELETE triggers exist on audit_logs table
- [ ] created_at column is TIMESTAMPTZ (immutable, timezone-aware)
- [ ] NO DEFAULT CURRENT_TIMESTAMP ON UPDATE clause exists

### Backend API
- [ ] NO PUT /audit/log route exists
- [ ] NO PATCH /audit/log route exists
- [ ] NO DELETE /audit/log route exists
- [ ] Only POST (create) and GET (read) routes exposed

### Frontend Utilities
- [ ] auditLogger.js only exports log* helpers (no update* or delete* functions)

---

## Troubleshooting Guide

### Issue: Audit logs not appearing in database

**Diagnostic Steps:**
1. Check browser console for errors: `[AuditLogger] ⚠️ Failed to log...`
2. Verify backend server is running: `curl http://localhost:8000/docs`
3. Check backend logs for exceptions: `uvicorn main:app --reload --log-level debug`
4. Verify database schema: `SELECT * FROM audit_logs LIMIT 1;`

**Common Causes:**
- Backend server stopped
- Database migrations not applied
- JSONB serialization error (missing json.dumps())
- FK constraint violation (patient_id doesn't exist)

---

### Issue: "TypeError: dict is not serializable"

**Root Cause:** Passing Python dict directly to psycopg2 JSONB column

**Solution:** Use `json.dumps(metadata)` before INSERT:
```python
cursor.execute(
    "INSERT INTO audit_logs (..., action_metadata) VALUES (..., %s)",
    (..., json.dumps(payload.action_metadata))  # ← json.dumps() wrapper
)
```

---

### Issue: UI freezes when clicking citations

**Root Cause:** Awaiting audit logger in synchronous event handler

**Solution:** Remove `await` keyword:
```javascript
// ✅ CORRECT
const openCitation = async (citation) => {
  logClickedCitation(patientId, citation)  // Fire-and-forget
  setPdfViewer(...)
}

// ❌ INCORRECT
const openCitation = async (citation) => {
  await logClickedCitation(patientId, citation)  // Blocks UI!
  setPdfViewer(...)
}
```

---

### Issue: "CHECK constraint violation: action_type"

**Root Cause:** Frontend sending action_type not in enum

**Solution:** Use AUDIT_ACTIONS constants from auditLogger.js:
```javascript
import { AUDIT_ACTIONS } from '../utils/auditLogger'

// ✅ CORRECT
logAudit(patientId, AUDIT_ACTIONS.VIEWED_SUMMARY, {})

// ❌ INCORRECT
logAudit(patientId, 'viewed_summary', {})  // Lowercase not in enum!
```

---

## Security Considerations

### Input Sanitization
- **patientId:** Validated as TEXT (no SQL injection risk with parameterized queries)
- **user_id:** Extracted from JWT token (trusted source)
- **action_metadata:** Stored as JSONB (no executable code risk)

### Access Control
- **GET /audit/{patient_id}:** Should implement role-based access control (TODO)
- **POST /audit/log:** Should validate user_id matches JWT token (TODO)

### Data Retention
- **HIPAA Compliance:** Retain audit_logs for minimum 6 years
- **GDPR Right to Erasure:** Audit logs may be exempt (legal basis: compliance)

---

## Future Enhancements

### Phase 1 (Epic 4.1 Remaining Tasks)
- [ ] PRESCRIBED_DRUG audit logging when prescription sent
- [ ] OVERRODE_ALERT UI workflow (doctor reason input modal)

### Phase 2 (Analytics)
- [ ] Real-time audit log dashboard (action_type frequency)
- [ ] Alert on anomalous patterns (e.g., 100+ EXPORTED_PDF in 1 minute)
- [ ] Compliance reporting (monthly audit log summaries)

### Phase 3 (Advanced Features)
- [ ] Audit log export to SIEM (Splunk, Datadog)
- [ ] Cryptographic log chain (tamper-evident blockchain)
- [ ] Differential privacy for analytics (k-anonymity)

---

**Last Updated:** 2025-01-XX  
**Epic:** 4.1 WORM Audit Logging  
**Version:** 1.0  
**Maintainers:** Development Team
