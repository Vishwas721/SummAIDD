"""Pydantic schemas for TPA claim validation output (separate from summary schemas)."""

from enum import Enum
from typing import List
from pydantic import BaseModel, Field


class ClaimStatus(str, Enum):
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"


class ClaimValidationResult(BaseModel):
    """Strict schema for LLM traffic-light validation output."""
    status: ClaimStatus = Field(..., description="Traffic-light validation status")
    discrepancies: List[str] = Field(
        default_factory=list,
        description="List of human-readable discrepancy findings"
    )
