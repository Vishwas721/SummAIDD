-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

-- Create patients table
CREATE TABLE patients (
    patient_id SERIAL PRIMARY KEY,
    patient_demo_id TEXT UNIQUE NOT NULL,  -- Non-PHI identifier (e.g., "patient_jane_doe")
    patient_display_name TEXT NOT NULL,    -- Display name (e.g., "Jane Doe")
    age INT NULL,                          -- Age (demo data; non-PHI)
    sex TEXT NULL                          -- Sex ("M", "F", or "Unknown")
);

-- Create reports table with FK to patients
CREATE TABLE reports (
    report_id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    report_filepath_pointer TEXT NOT NULL,
    report_type TEXT,  -- e.g., "Radiology", "Pathology", "Lab"
    report_text_encrypted BYTEA NOT NULL
);

-- Create report_chunks table for RAG optimization
CREATE TABLE report_chunks (
    chunk_id SERIAL PRIMARY KEY,
    report_id INTEGER NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,
    chunk_text_encrypted BYTEA NOT NULL,
    report_vector vector(768) NOT NULL,
    source_metadata JSONB NOT NULL  -- Stores {'page': X, 'chunk_index': Y} for citations
);

-- Create indexes for performance
CREATE INDEX idx_reports_patient_id ON reports(patient_id);
CREATE INDEX idx_report_chunks_report_id ON report_chunks(report_id);
CREATE INDEX idx_report_chunks_vector ON report_chunks USING ivfflat (report_vector vector_cosine_ops);
CREATE INDEX idx_patients_demo_id ON patients(patient_demo_id);

-- Create patient_consents table for DPDP Act compliance (TPA Feature - Phase 1)
CREATE TABLE patient_consents (
    consent_id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    mobile_number BYTEA NOT NULL,  -- Encrypted mobile number for consent verification
    consent_status BOOLEAN NOT NULL DEFAULT FALSE,  -- TRUE = consented, FALSE = pending/denied
    requested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP NULL  -- NULL until patient responds
);

-- Create insurance_claims table for TPA validation workflow
CREATE TABLE insurance_claims (
    claim_id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'RED', 'YELLOW', 'GREEN')),  -- Traffic light indicator
    discrepancies JSONB NULL,  -- Stores validation issues as JSON: {"field": "issue description"}
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for TPA tables
CREATE INDEX idx_patient_consents_patient_id ON patient_consents(patient_id);
CREATE INDEX idx_insurance_claims_patient_id ON insurance_claims(patient_id);
CREATE INDEX idx_insurance_claims_status ON insurance_claims(status);

-- ============================================================================
-- EPIC 4.1: WORM Audit Logging (Write Once, Read Many)
-- ============================================================================

-- Audit Log Table - Immutable tracking of all doctor interactions
CREATE TABLE audit_logs (
    log_id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,  -- doctor/MA username
    action_type TEXT NOT NULL CHECK (action_type IN ('VIEWED_SUMMARY', 'CLICKED_CITATION', 'PRESCRIBED_DRUG', 'EXPORTED_PDF', 'OVERRODE_ALERT')),
    action_metadata JSONB,  -- flexible context: {citation_id, drug_name, pdf_url, etc.}
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_audit_logs_patient ON audit_logs(patient_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);

-- Alert Override Table - Justification for overriding allergy alerts
CREATE TABLE alert_overrides (
    override_id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    drug_name TEXT NOT NULL,
    allergy_keyword TEXT NOT NULL,  -- the specific allergy substring that triggered the alert
    doctor_reason TEXT NOT NULL,  -- why the override was justified
    overridden_by TEXT NOT NULL,  -- doctor username
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_alert_overrides_patient ON alert_overrides(patient_id);