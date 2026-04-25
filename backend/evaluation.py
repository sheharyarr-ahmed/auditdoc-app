"""Checklist evaluation against extracted PDF chunks.

Calls Anthropic Claude with tool-use to produce strict-JSON `Finding` objects.
See `.claude/skills/claude-structured-output.md` for the pattern and
`.claude/rules/citations-mandatory.md` for the citation-downgrade rule.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from typing import Any

from anthropic import AsyncAnthropic

from schemas import (
    ChecklistItem,
    Chunk,
    EvaluationResult,
    EvaluationStatus,
    Finding,
    FindingStatus,
    Severity,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-6"
PER_ITEM_TIMEOUT_S = 30.0
OVERALL_TIMEOUT_S = 120.0
CONCURRENCY = 4

FINDING_TOOL: dict[str, Any] = {
    "name": "record_finding",
    "description": "Record an audit finding for a single checklist item, with mandatory citations for any FAIL.",
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["PASS", "FAIL", "PARTIAL", "NOT_APPLICABLE"],
                "description": "PASS if the document fully demonstrates the requirement; FAIL if it explicitly violates it; PARTIAL if partial evidence; NOT_APPLICABLE if the requirement does not apply.",
            },
            "severity": {
                "type": "string",
                "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                "description": "Severity if the finding is FAIL or PARTIAL. Echo the checklist item's severity unless you have strong reason to deviate.",
            },
            "description": {
                "type": "string",
                "description": "One-sentence explanation of the finding, citing what the document does or fails to do.",
            },
            "supporting_chunk_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "0-indexed positions in the chunks list that justify this finding. REQUIRED for FAIL findings. Use [] only when status is NOT_APPLICABLE.",
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "Self-reported confidence in the finding.",
            },
        },
        "required": ["status", "severity", "description", "supporting_chunk_ids", "confidence"],
    },
}


# --- Checklists -------------------------------------------------------------
# Placeholder content per the MVP plan — three items per checklist, enough to
# exercise the full pipeline. Refine when we wire real reference docs.

_CHECKLISTS: dict[str, list[ChecklistItem]] = {
    "soc2_trust_services": [
        ChecklistItem(
            id="soc2_cc6_1",
            title="Logical Access Controls",
            description="The system uses authentication and authorization to restrict access to information assets to authorized users only.",
            severity=Severity.HIGH,
        ),
        ChecklistItem(
            id="soc2_cc6_7",
            title="Encryption in Transit",
            description="Data transmitted over public networks is encrypted using current industry-standard protocols (e.g., TLS 1.2+).",
            severity=Severity.HIGH,
        ),
        ChecklistItem(
            id="soc2_cc7_2",
            title="Audit Logging",
            description="System events relevant to security are logged, retained, and reviewed.",
            severity=Severity.MEDIUM,
        ),
    ],
    "esg_basic": [
        ChecklistItem(
            id="esg_e1",
            title="Greenhouse Gas Emissions Disclosure",
            description="The organization discloses Scope 1 and Scope 2 GHG emissions for the reporting period.",
            severity=Severity.HIGH,
        ),
        ChecklistItem(
            id="esg_s1",
            title="Workforce Diversity Disclosure",
            description="The organization reports workforce composition by gender and, where lawful, by other diversity dimensions.",
            severity=Severity.MEDIUM,
        ),
        ChecklistItem(
            id="esg_g1",
            title="Board Independence",
            description="A majority of the board of directors is independent of management.",
            severity=Severity.HIGH,
        ),
    ],
    "code_review_security": [
        ChecklistItem(
            id="cr_auth",
            title="Authentication Implementation",
            description="Authentication uses well-vetted libraries and enforces credential storage best practices (e.g., bcrypt/argon2; no plaintext passwords).",
            severity=Severity.CRITICAL,
        ),
        ChecklistItem(
            id="cr_input",
            title="Input Validation",
            description="User-supplied input is validated, encoded, or parameterized at trust boundaries to prevent injection.",
            severity=Severity.HIGH,
        ),
        ChecklistItem(
            id="cr_secrets",
            title="Secret Management",
            description="API keys, tokens, and credentials are not committed to source control and are loaded from environment variables or a secret manager.",
            severity=Severity.CRITICAL,
        ),
    ],
}


def load_checklist(checklist_id: str) -> list[ChecklistItem]:
    """Load a checklist by id. Raises ValueError on unknown id."""
    items = _CHECKLISTS.get(checklist_id)
    if items is None:
        raise ValueError(f"Unknown checklist_id: {checklist_id}")
    return items


# --- Prompt building --------------------------------------------------------


def _build_prompt(item: ChecklistItem, chunks: list[Chunk]) -> str:
    chunk_lines: list[str] = []
    for i, c in enumerate(chunks):
        # Cap each chunk's text to keep prompts bounded; full text is in the doc.
        excerpt = c.text if len(c.text) <= 600 else c.text[:600] + "…"
        chunk_lines.append(f"[{i}] (page {c.page} · {c.section}) {excerpt}")
    chunks_block = "\n".join(chunk_lines) if chunk_lines else "(no extractable text)"

    return (
        f"You are auditing a document for compliance with a single checklist item.\n\n"
        f"CHECKLIST ITEM\n"
        f"  id: {item.id}\n"
        f"  title: {item.title}\n"
        f"  severity: {item.severity.value}\n"
        f"  requirement: {item.description}\n\n"
        f"DOCUMENT CHUNKS (0-indexed; cite by id in supporting_chunk_ids)\n"
        f"{chunks_block}\n\n"
        f"Decide PASS / FAIL / PARTIAL / NOT_APPLICABLE. Cite supporting chunks "
        f"by their 0-indexed id. A FAIL **must** include at least one supporting_chunk_id; "
        f"if you cannot cite, return PARTIAL instead. Call the record_finding tool."
    )


# --- Single-item evaluation -------------------------------------------------


def _parse_tool_response(response: Any, item: ChecklistItem, chunks: list[Chunk]) -> Finding:
    """Pull the record_finding tool block out of an Anthropic response and
    convert it into a validated `Finding`. Enforces the citation-downgrade rule.
    """
    tool_block = next(
        (b for b in response.content if getattr(b, "type", None) == "tool_use"),
        None,
    )
    if tool_block is None:
        raise ValueError("Model did not call the record_finding tool")

    data = tool_block.input
    raw_ids = data.get("supporting_chunk_ids", []) or []

    # Bounds-check: model can hallucinate indices.
    cited = [chunks[i] for i in raw_ids if isinstance(i, int) and 0 <= i < len(chunks)]

    status = FindingStatus(data["status"])
    severity = Severity(data["severity"])

    # Defense-in-depth for citations-mandatory rule: downgrade FAIL→PARTIAL
    # rather than letting the schema validator raise.
    if status == FindingStatus.FAIL and not cited:
        logger.warning("item=%s: FAIL with no citations → downgrading to PARTIAL", item.id)
        status = FindingStatus.PARTIAL

    return Finding(
        item_id=item.id,
        status=status,
        severity=severity,
        description=data["description"],
        supporting_chunks=cited,
        confidence=float(data["confidence"]),
    )


async def evaluate_single_item(
    item: ChecklistItem,
    chunks: list[Chunk],
    *,
    client: AsyncAnthropic,
    model: str = DEFAULT_MODEL,
    timeout_s: float = PER_ITEM_TIMEOUT_S,
) -> Finding:
    """Run one checklist item through the LLM and return a validated `Finding`."""
    prompt = _build_prompt(item, chunks)
    t0 = time.perf_counter()
    try:
        async with asyncio.timeout(timeout_s):
            response = await client.messages.create(
                model=model,
                max_tokens=1024,
                tools=[FINDING_TOOL],
                tool_choice={"type": "tool", "name": "record_finding"},
                messages=[{"role": "user", "content": prompt}],
            )
    except asyncio.TimeoutError as exc:
        raise TimeoutError(f"item {item.id} exceeded {timeout_s}s") from exc

    finding = _parse_tool_response(response, item, chunks)
    logger.info(
        "item=%s status=%s severity=%s citations=%d duration=%.2fs",
        item.id,
        finding.status.value,
        finding.severity.value,
        len(finding.supporting_chunks),
        time.perf_counter() - t0,
    )
    return finding


# --- Full checklist ---------------------------------------------------------


def _summarize(findings: list[Finding]) -> str:
    """Build a one-line summary of finding counts grouped by severity."""
    if not findings:
        return "No findings"
    flagged = [f for f in findings if f.status in (FindingStatus.FAIL, FindingStatus.PARTIAL)]
    if not flagged:
        return f"{len(findings)} item(s) — all PASS / N/A"
    counts: dict[str, int] = {}
    for f in flagged:
        counts[f.severity.value] = counts.get(f.severity.value, 0) + 1
    parts = [f"{counts.get(s, 0)} {s}" for s in ("CRITICAL", "HIGH", "MEDIUM", "LOW") if counts.get(s)]
    return ", ".join(parts)


async def evaluate_checklist(
    document_id: str,
    checklist_id: str,
    chunks: list[Chunk],
    *,
    client: AsyncAnthropic | None = None,
    model: str = DEFAULT_MODEL,
    overall_timeout_s: float = OVERALL_TIMEOUT_S,
    concurrency: int = CONCURRENCY,
) -> EvaluationResult:
    """Evaluate every item in a checklist concurrently and aggregate findings."""
    items = load_checklist(checklist_id)
    if client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        client = AsyncAnthropic(api_key=api_key)

    semaphore = asyncio.Semaphore(concurrency)

    async def _run(item: ChecklistItem) -> Finding:
        async with semaphore:
            return await evaluate_single_item(item, chunks, client=client, model=model)

    evaluation_id = str(uuid.uuid4())
    logger.info(
        "evaluate: starting evaluation_id=%s checklist=%s items=%d chunks=%d",
        evaluation_id,
        checklist_id,
        len(items),
        len(chunks),
    )

    try:
        async with asyncio.timeout(overall_timeout_s):
            findings = await asyncio.gather(*(_run(it) for it in items))
    except asyncio.TimeoutError:
        logger.error("evaluate: overall timeout after %.0fs", overall_timeout_s)
        return EvaluationResult(
            evaluation_id=evaluation_id,
            document_id=document_id,
            checklist_id=checklist_id,
            status=EvaluationStatus.FAILED,
            findings=[],
            summary=f"Evaluation timed out after {overall_timeout_s:.0f}s",
        )

    return EvaluationResult(
        evaluation_id=evaluation_id,
        document_id=document_id,
        checklist_id=checklist_id,
        status=EvaluationStatus.COMPLETED,
        findings=list(findings),
        summary=_summarize(list(findings)),
    )
