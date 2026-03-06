# SummAID Product Q&A (Strict, Source-Based)

This file answers the provided questions using only what is documented or implemented in the repository. If something is not implemented or not documented, it is explicitly marked as such.

## Level 1: The Basics (Warm-up)

### 1) On-Premise vs Cloud ("Fortress Model")
**Question:** "I see you switched from cloud APIs to a 'Fortress Model'. Why was On-Premise strictly necessary for this use case, and what trade-offs did that introduce in terms of model performance?"

**Answer (strict):**
- The repo describes the product as **on-premise with zero cloud dependency** for **HIPAA/DPDPA compliance** and to ensure **no PHI leaves the hospital network**. That is the documented reason for on-prem deployment.
- The term "Fortress Model" is not used in the repository.
- **Trade-offs in model performance are not documented** in the repo, so we cannot claim any specific performance impact.

Sources: [README.md](README.md), [documents/ACCURACY_QUICK_REFERENCE.md](documents/ACCURACY_QUICK_REFERENCE.md)

### 2) Model Choice (Qwen 2.5:14b quantized vs Llama 3/Mistral)
**Question:** "You are using Qwen 2.5:14b (quantized) for generation. Why did you choose Qwen over Llama 3 or Mistral? How does it handle the specific JSON reasoning required for your schema?"

**Answer (strict):**
- The repository does **not** use Qwen 2.5:14b as the primary generation model.
- The documented default generation model is **llama3:8b** (via Ollama). Qwen appears only as a **fallback** model list in configuration.
- There is **no mention of Mistral** in the repository configuration.
- JSON output is enforced via **parallel prompts + Pydantic schema validation** (AIResponseSchema), but there is **no documented benchmark** comparing Qwen vs Llama for JSON reasoning.

Sources: [README.md](README.md), [backend/config.py](backend/config.py), [documentation/PARALLEL_PROMPTS_REFACTORING.md](documentation/PARALLEL_PROMPTS_REFACTORING.md), [backend/PARALLEL_PROMPTS_GUIDE.md](backend/PARALLEL_PROMPTS_GUIDE.md)

### 3) "Glass Box" citation system
**Question:** "Explain your 'Glass Box' citation system. How exactly do you technically link a generated sentence back to a specific page in a PDF?"

**Answer (strict):**
- Each PDF is split into **chunks** with metadata that includes **page number** and **chunk_index**.
- For summaries and chat, citations include: `report_id`, `source_text_preview`, `source_full_text`, and `source_metadata` (which includes `page` and `chunk_index`).
- The frontend uses the `report_id` to open the PDF and the citation metadata to show the relevant source context. This is a **chunk-level** link, not a token-level alignment.

Sources: [backend/schema.sql](backend/schema.sql), [backend/main.py](backend/main.py), [backend/seed.py](backend/seed.py), [backend/CHAT_ENDPOINT.md](backend/CHAT_ENDPOINT.md)

## Level 2: Architecture & System Design

### 4) RAG encryption/decryption latency
**Question:** "Your database schema splits data into report_chunks with chunk_text_encrypted and report_vector. How do you handle the encryption/decryption latency during a real-time vector search? Do you search on encrypted vectors, or do you decrypt on the fly?"

**Answer (strict):**
- Vectors are stored in **pgvector** as `report_vector` and are **not encrypted**.
- Vector similarity search is executed over `report_vector` directly.
- `chunk_text_encrypted` is decrypted **on the fly** in SQL using `pgp_sym_decrypt(...)` when retrieving chunks.
- There is **no documented latency mitigation** beyond the hybrid retrieval design and limits; performance targets are stated in the test plan, but no specific optimization for decryption is described.

Sources: [backend/schema.sql](backend/schema.sql), [backend/main.py](backend/main.py), [README.md](README.md), [documents/Test_Plan.md](documents/Test_Plan.md)

### 5) Orchestration: "Prepare Chart" flow (parallel vs sequential)
**Question:** "You mention using LangChain with asyncio for parallel execution. Can you walk me through the exact flow when a user clicks 'Prepare Chart'? What is happening in parallel vs. sequentially?"

**Answer (strict):**
- **LangChain is not used** in this repo. Parallel execution is implemented using **asyncio**.
- The "Prepare Chart" action corresponds to the **MA generating a summary** via `POST /summarize/{patient_id}`.
- **Sequential steps (backend):**
  1. Retrieve and decrypt chunks for the patient.
  2. Assemble full context.
  3. Classify specialty.
- **Parallel steps (backend):**
  - The universal extractions (evolution, current status, plan) run in **parallel** via `asyncio.gather`.
- **Conditional step:**
  - If specialty is oncology or speech, run the corresponding specialty extractor.
- The backend persists the summary and sets `chart_prepared_at` when the summary is saved.

Sources: [backend/main.py](backend/main.py), [backend/PARALLEL_PROMPTS_GUIDE.md](backend/PARALLEL_PROMPTS_GUIDE.md), [documentation/PARALLEL_PROMPTS_REFACTORING.md](documentation/PARALLEL_PROMPTS_REFACTORING.md)

### 6) Scalability: RabbitMQ + HashiCorp Vault
**Question:** "Your v3 Blueprint mentions introducing RabbitMQ and HashiCorp Vault. Why introduce that complexity? What specific failure scenario in the MVP were you trying to solve with a message queue?"

**Answer (strict):**
- The repository contains a **comment** in backend code stating that the current `.env` key management **must be replaced** with **HashiCorp Vault** before any pilot.
- **RabbitMQ is not present** in code or docs in this repository.
- **No specific message-queue failure scenario is documented**, so we cannot claim an MVP failure that RabbitMQ was intended to fix.

Sources: [backend/main.py](backend/main.py)

## Level 3: The "Grill" (Agentic & AI Specifics)

### 7) Embeddings and chunking strategy
**Question:** "You used nomic-embed-text with a dimension of 768. Medical records are messy and unstructured. How did you handle chunking? Did you use fixed-size chunks, or did you implement semantic chunking to keep medical context together?"

**Answer (strict):**
- Embeddings use **nomic-embed-text** with **768 dimensions**.
- Chunking is **fixed-size with overlap** (default 500 chars with 100 overlap), and chunks preserve **page** and **chunk_index** metadata.
- There is **no semantic chunking** implementation in this repo.

Sources: [README.md](README.md), [backend/seed.py](backend/seed.py), [backend/main.py](backend/main.py)

### 8) Multi-Specialty Prompt Router
**Question:** "You mention a Multi-Specialty Prompt Router (Oncology vs. Speech). How does this router work? Is it a classifier agent that decides which prompt to use, or is it hard-coded logic?"

**Answer (strict):**
- The router is implemented as a **classification prompt** that returns `oncology`, `speech`, or `general`.
- This is **LLM-based classification**, not a hard-coded rules-only router (though it uses explicit keyword-based instructions in the prompt).

Sources: [backend/parallel_prompts.py](backend/parallel_prompts.py), [backend/PARALLEL_PROMPTS_GUIDE.md](backend/PARALLEL_PROMPTS_GUIDE.md)

### 9) "Smart RFI" and hallucination control
**Question:** "In your 'Smart RFI' feature, how do you prevent the model from hallucinating missing evidence? If the model says 'Lab report missing,' how do you verify it's actually missing and not just buried in a bad OCR scan?"

**Answer (strict):**
- A **"Smart RFI" feature is not documented or implemented** in this repo.
- Hallucination prevention is handled via **prompt rules** (explicitly instructing "no hallucinations") and evaluation checks, but there is **no automated verification** to confirm that a missing item is truly missing versus OCR failure.
- OCR fallback exists in the **data seeding pipeline** for low-text PDFs, but **OCR is listed as Phase 2** in the test plan for general workflows.

Sources: [backend/parallel_prompts.py](backend/parallel_prompts.py), [documents/ONCOLOGY_SUMMARY_MULTI_STEP_PROMPTS.md](documents/ONCOLOGY_SUMMARY_MULTI_STEP_PROMPTS.md), [backend/seed.py](backend/seed.py), [documents/Test_Plan.md](documents/Test_Plan.md)

## Additional Questions That Are Important (with strict answers)

### A1) What models and embeddings are actually used in production today?
**Answer (strict):**
- Generation: **llama3:8b** via Ollama (default). Fallbacks include **qwen2.5:7b/3b** and **llama3.2:3b**.
- Embeddings: **nomic-embed-text**, 768-dim, stored in pgvector.

Sources: [README.md](README.md), [backend/config.py](backend/config.py), [backend/main.py](backend/main.py)

### A2) What are the performance targets and observed results?
**Answer (strict):**
- Targets (test plan): summary <120s, retrieval/chat <10s, safety-check <5s.
- Observed results (test summary): summary ~45s, chat ~6.2s, safety-check ~3.8s.

Sources: [documents/Test_Plan.md](documents/Test_Plan.md), [documents/Test_Result_Summary.md](documents/Test_Result_Summary.md)

### A3) What is currently out of scope or planned for Phase 2?
**Answer (strict):**
- Out of scope: cloud deployment testing, EMR/FHIR integration, patient-facing UI, OCR for image-only PDFs, advanced visualizations.
- Planned Phase 2: FHIR/EMR integration, EMR SSO, patient-facing summaries, advanced trends, encrypted cloud backup.

Sources: [README.md](README.md), [documents/Test_Plan.md](documents/Test_Plan.md)

### A4) How are citations exposed to the UI and verified in tests?
**Answer (strict):**
- The API returns a `citations` array with chunk/page metadata and source text.
- Tests confirm that key findings include clickable citations pointing to source reports.

Sources: [backend/CHAT_ENDPOINT.md](backend/CHAT_ENDPOINT.md), [documents/Test_Result_Summary.md](documents/Test_Result_Summary.md)

### A5) What security controls are explicitly implemented?
**Answer (strict):**
- **AES-256 encryption at rest** using pgcrypto for all report text.
- On-prem-only deployment, TLS for internal transport, and role-based access (MA vs DOCTOR).

Sources: [README.md](README.md), [backend/schema.sql](backend/schema.sql)
