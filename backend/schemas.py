"""Pydantic v2 schemas for AuditDoc.

These models are the contract between extraction.py, evaluation.py, and the
FastAPI routes in main.py. They are also mirrored in frontend/lib/types.ts —
keep the two in sync if you change anything here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FindingStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class EvaluationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Chunk(BaseModel):
    page: int = Field(..., ge=1, description="1-indexed PDF page number")
    section: str = Field(..., description="Section heading or 'body' if none detected")
    text: str = Field(..., min_length=1)
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


class ChecklistItem(BaseModel):
    id: str
    title: str
    description: str
    severity: Severity


class Finding(BaseModel):
    item_id: str
    status: FindingStatus
    severity: Severity
    description: str
    supporting_chunks: list[Chunk] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("supporting_chunks")
    @classmethod
    def _fail_requires_citation(cls, v: list[Chunk], info) -> list[Chunk]:
        # Mirror of rules/citations-mandatory.md: a FAIL must cite.
        status = info.data.get("status")
        if status == FindingStatus.FAIL and not v:
            raise ValueError("FAIL findings must include at least one supporting_chunk")
        return v


class EvaluationResult(BaseModel):
    evaluation_id: str
    document_id: str
    checklist_id: str
    status: EvaluationStatus
    findings: list[Finding] = Field(default_factory=list)
    summary: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    size: int
    status: str = "uploaded"


class EvaluateRequest(BaseModel):
    document_id: str
    checklist_id: str


class ErrorResponse(BaseModel):
    error: str
    status_code: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    detail: Optional[str] = None
