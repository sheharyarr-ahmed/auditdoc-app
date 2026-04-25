"""AuditDoc FastAPI entry point.

Routes (per CLAUDE.md API CONTRACTS):
    GET  /health
    POST /upload                  multipart, max 50MB
    POST /evaluate                JSON {document_id, checklist_id}
    GET  /results/{evaluation_id}
"""

from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from anthropic import AuthenticationError, RateLimitError
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import evaluation
import extraction
from schemas import (
    Chunk,
    ErrorResponse,
    EvaluateRequest,
    EvaluationResult,
    UploadResponse,
)

# Look for .env.local at the project root, then fall back to .env in CWD.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env.local")
load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("auditdoc")

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))  # default 50MB per CLAUDE.md constraint #4
PDF_MAGIC = b"%PDF-"

# Comma-separated list of allowed origins. Override per environment.
_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

# In-memory stores. Replace with Supabase in the database phase.
DOCUMENTS: dict[str, dict[str, object]] = {}
EVALUATIONS: dict[str, EvaluationResult] = {}


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("AuditDoc backend starting")
    yield
    logger.info("AuditDoc backend stopping")


app = FastAPI(title="AuditDoc API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _error(status: int, message: str, detail: str | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=ErrorResponse(error=message, status_code=status, detail=detail).model_dump(mode="json"),
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)) -> UploadResponse:
    try:
        contents = await file.read()
    except Exception as exc:  # pragma: no cover — read failures are rare
        logger.error("upload read failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to read upload")

    size = len(contents)
    if size == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if size > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_UPLOAD_BYTES} bytes")
    if not contents.startswith(PDF_MAGIC):
        raise HTTPException(status_code=400, detail="File is not a valid PDF (magic-byte check failed)")

    document_id = str(uuid.uuid4())
    DOCUMENTS[document_id] = {
        "filename": file.filename or "upload.pdf",
        "size": size,
        "bytes": contents,
    }
    logger.info("upload ok: document_id=%s size=%d", document_id, size)
    return UploadResponse(document_id=document_id, filename=file.filename or "upload.pdf", size=size)


@app.post("/evaluate", response_model=EvaluationResult)
async def evaluate(req: EvaluateRequest) -> EvaluationResult:
    doc = DOCUMENTS.get(req.document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="document_id not found")

    try:
        chunks: list[Chunk] = extraction.extract_pdf_with_metadata_from_bytes(doc["bytes"])  # type: ignore[arg-type]
        result = await evaluation.evaluate_checklist(
            document_id=req.document_id,
            checklist_id=req.checklist_id,
            chunks=chunks,
        )
    except TimeoutError as exc:
        logger.error("evaluate timeout: %s", exc)
        raise HTTPException(status_code=503, detail="Evaluation timed out")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except AuthenticationError:
        logger.error("evaluate failed: anthropic auth error (check ANTHROPIC_API_KEY)")
        raise HTTPException(status_code=503, detail="Upstream auth failure")
    except RateLimitError:
        logger.warning("evaluate failed: anthropic rate-limited")
        raise HTTPException(status_code=429, detail="Rate-limited by upstream LLM")
    except Exception as exc:
        logger.error("evaluate failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Evaluation failed")

    EVALUATIONS[result.evaluation_id] = result
    return result


@app.get("/results/{evaluation_id}", response_model=EvaluationResult)
async def results(evaluation_id: str) -> EvaluationResult:
    result = EVALUATIONS.get(evaluation_id)
    if result is None:
        raise HTTPException(status_code=404, detail="evaluation_id not found")
    return result
