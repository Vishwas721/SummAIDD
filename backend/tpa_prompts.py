"""Synchronous LLM validation prompts for TPA claim document checks."""

import os
import json
import re
from typing import Any
import requests
import logging

from tpa_schemas import ClaimValidationResult

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
# Fallback to the same model the summarization engine uses, or default to a solid instruct model
VALIDATION_MODEL = os.getenv("LLM_MODEL_NAME", "llama3.2:3b-instruct-q4_K_M")


def _extract_json_block(text: str) -> str:
    """Extract a JSON object from potentially noisy model output."""
    if not text:
        return ""

    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    if cleaned.startswith("{") and cleaned.endswith("}"):
        return cleaned

    match = re.search(r"\{[\s\S]*\}", cleaned)
    return match.group(0) if match else ""


def _validate_claim_document(extracted_text: str) -> ClaimValidationResult:
    """
    Validate claim document text using a local LLM and return strict traffic-light JSON.
    """
    if not extracted_text or not extracted_text.strip():
        return ClaimValidationResult(
            status="RED",
            discrepancies=["Claim document text is empty or unreadable"],
        )

    prompt = f"""You are a strict TPA (insurance claims) validator for the Clear2Go system.

Your job is to check the extracted claim document text against basic insurance validation rules and return ONLY JSON.

Traffic Light Rules:
- RED (Critical): Missing mandatory information or severe inconsistencies.
  Examples: missing patient name, missing diagnosis, missing provider details, claim text too incomplete to adjudicate.
- YELLOW (Warning): Financial or policy-adjacent discrepancies that may need manual review.
  Examples: billed amount appears unusually high vs pre-auth mention, duplicate line items, unclear payable totals.
- GREEN (Clean): Basic checks pass and no major discrepancy found.

STRICT OUTPUT REQUIREMENTS:
1. Return EXACTLY one JSON object.
2. Do not include markdown, code fences, explanation text, or extra keys.
3. Use this schema exactly:
   {{
     "status": "RED|YELLOW|GREEN",
     "discrepancies": ["string", "string"]
   }}
4. If no issues, return an empty discrepancies list.

Extracted Claim Document Text:
{extracted_text[:12000]}

Return JSON now.
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": VALIDATION_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "num_ctx": 4096,
                    "top_p": 0.9,
                },
            },
            timeout=120,
        )
        
        payload = response.json() if hasattr(response, "json") else {}
        raw_text = (payload or {}).get("response", "") if response.status_code == 200 else ""
        json_text = _extract_json_block(raw_text)

        if not json_text:
            logger.warning(f"LLM validation failed to produce JSON: {raw_text[:200]}")
            return ClaimValidationResult(
                status="YELLOW",
                discrepancies=["LLM returned non-JSON output; manual TPA review required"],
            )

        parsed = json.loads(json_text)
        return ClaimValidationResult.model_validate(parsed)

    except Exception as exc:
        logger.exception("Validation engine fallback triggered")
        return ClaimValidationResult(
            status="YELLOW",
            discrepancies=[f"Validation engine fallback: {str(exc)}"],
        )