# TPA Consent Management API - Quick Reference

## Overview
FastAPI endpoints for DPDP Act-compliant consent management before TPA validation.

**Router Prefix:** `/tpa`  
**Tags:** `TPA Consent`

---

## Endpoints

### 1️⃣ **POST /tpa/consent/{patient_id}** - Request Consent

**Description:** Initiates a consent request for a patient. Creates a pending record and simulates sending OTP via SMS.

**Path Parameters:**
- `patient_id` (int) - Patient ID requiring consent

**Request Body:**
```json
{
  "mobile_number": "+919876543210"
}
```

**Response Model:** `PatientConsentResponse`
```json
{
  "consent_id": 1,
  "patient_id": 123,
  "consent_status": false,
  "requested_at": "2024-12-01T10:30:00Z",
  "responded_at": null
}
```

**Status Codes:**
- `200` - Consent request created successfully
- `400` - Consent already exists for this patient
- `404` - Patient not found
- `500` - Database error

**Security:** Mobile number is encrypted using `pgp_sym_encrypt()` before storage.

---

### 2️⃣ **POST /tpa/consent/{patient_id}/verify** - Verify OTP

**Description:** Verifies OTP and grants consent. Updates `consent_status` to `TRUE`.

**Path Parameters:**
- `patient_id` (int) - Patient ID to verify consent for

**Request Body:**
```json
{
  "otp": "123456"
}
```

**Response Model:** `PatientConsentResponse`
```json
{
  "consent_id": 1,
  "patient_id": 123,
  "consent_status": true,
  "requested_at": "2024-12-01T10:30:00Z",
  "responded_at": "2024-12-01T15:45:00Z"
}
```

**Status Codes:**
- `200` - OTP verified, consent granted
- `400` - Invalid OTP format or already verified
- `404` - No consent request found
- `500` - Database error

**Phase 1 Mock:** Accepts any 4-6 digit numeric OTP. Production will integrate real SMS gateway.

---

### 3️⃣ **GET /tpa/consent/{patient_id}** - Get Consent Status

**Description:** Retrieves current consent status for a patient. Does not expose encrypted mobile number.

**Path Parameters:**
- `patient_id` (int) - Patient ID to check consent for

**Response Model:** `PatientConsentResponse`
```json
{
  "consent_id": 1,
  "patient_id": 123,
  "consent_status": true,
  "requested_at": "2024-12-01T10:30:00Z",
  "responded_at": "2024-12-01T15:45:00Z"
}
```

**Status Codes:**
- `200` - Consent status retrieved
- `404` - No consent record found
- `500` - Database error

**Use Case:** Check if patient has granted DPDP consent before TPA operations.

---

## Database Tables

### `patient_consents`
```sql
CREATE TABLE patient_consents (
    consent_id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    mobile_number BYTEA NOT NULL,  -- Encrypted
    consent_status BOOLEAN NOT NULL DEFAULT FALSE,
    requested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP NULL
);
```

**Indexes:**
- `idx_patient_consents_patient_id` on `patient_id`

---

## Testing

### Run Test Suite
```bash
# Ensure server is running
cd backend
python start_server.ps1  # or: uvicorn main:app --reload

# In another terminal
python test_tpa_consent.py
```

### Manual Testing (curl)
```bash
# 1. Request consent
curl -X POST http://localhost:8000/tpa/consent/1 \
  -H "Content-Type: application/json" \
  -d '{"mobile_number": "+919876543210"}'

# 2. Verify OTP
curl -X POST http://localhost:8000/tpa/consent/1/verify \
  -H "Content-Type: application/json" \
  -d '{"otp": "123456"}'

# 3. Get consent status
curl http://localhost:8000/tpa/consent/1
```

### Swagger UI
Access interactive API docs at: `http://localhost:8000/docs`

Look for the **TPA Consent** section with all three endpoints.

---

## Error Handling

All endpoints follow consistent error handling:
- Database connections are properly closed in `finally` blocks
- Transactions are rolled back on errors
- HTTPExceptions provide clear error messages
- All errors are logged with `logger.exception()`

---

## Async Execution

All endpoints use `async def` for non-blocking execution:
- Database operations run in thread pool (via psycopg2)
- No blocking of FastAPI event loop
- Concurrent requests handled efficiently

---

## Security Notes

### Phase 1 (Current)
- ✅ Mobile numbers encrypted with `pgp_sym_encrypt()`
- ✅ Encryption key from `.env` file
- ⚠️ Mock OTP accepts any 4-6 digit code
- ⚠️ No rate limiting on OTP attempts

### Production Requirements (Phase 2+)
- 🔒 Migrate to HashiCorp Vault for key management
- 🔒 Integrate real SMS gateway (Twilio, AWS SNS)
- 🔒 Implement OTP expiry (5 min timeout)
- 🔒 Add rate limiting (max 3 OTP attempts)
- 🔒 Log all consent events for audit trail

---

## Integration Example

```python
import requests

# Complete consent workflow
patient_id = 123
mobile = "+919876543210"

# Step 1: Request consent
response = requests.post(
    f"http://localhost:8000/tpa/consent/{patient_id}",
    json={"mobile_number": mobile}
)
print(f"Consent requested: {response.json()}")

# Step 2: User receives OTP (simulated in logs)
# Step 3: Verify OTP
response = requests.post(
    f"http://localhost:8000/tpa/consent/{patient_id}/verify",
    json={"otp": "123456"}
)
print(f"Consent verified: {response.json()}")

# Step 4: Check status before TPA operations
response = requests.get(
    f"http://localhost:8000/tpa/consent/{patient_id}"
)
consent = response.json()
if consent["consent_status"]:
    print("✅ Proceed with TPA validation")
else:
    print("❌ Consent required before TPA operations")
```

---

## Files Modified

### New Files
- `backend/routers/tpa_router.py` - TPA consent router
- `backend/test_tpa_consent.py` - Test suite
- `documentation/TPA_CONSENT_API.md` - This documentation

### Modified Files
- `backend/schema.sql` - Added `patient_consents` table
- `backend/schemas.py` - Added `PatientConsentCreate` and `PatientConsentResponse` models
- `backend/main.py` - Imported and included `tpa_router`

---

## Next Steps (Future Tasks)

1. **Task 3:** Insurance claim validation endpoints
2. **Task 4:** TPA document upload and OCR extraction
3. **Task 5:** AI-powered discrepancy detection
4. **Task 6:** Frontend consent UI components

---

## Definition of Done ✅

- [x] Endpoints correctly routed with `/tpa` prefix
- [x] Swagger/OpenAPI documentation auto-generated
- [x] Database insertions handle FK errors gracefully (404 for missing patient)
- [x] API logic does not block main thread (async/await)
- [x] Test suite created and validated
- [x] Error logging implemented
- [x] Security measures (encryption) in place
