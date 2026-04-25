"""Tests for evaluation.py.

Run from backend/ directory:
    .venv/bin/python -m tests.test_evaluation

Offline tests (load_checklist, parse_tool_response, citation downgrade) always run.
The live-API test runs only if ANTHROPIC_API_KEY is set to a real key (anything
not starting with 'sk-ant-PLACEHOLDER').
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load .env.local from project root so live tests pick up ANTHROPIC_API_KEY.
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env.local")

import fitz  # noqa: E402

import evaluation  # noqa: E402
from evaluation import _parse_tool_response, evaluate_checklist, load_checklist  # noqa: E402
from extraction import extract_pdf_with_metadata_from_bytes  # noqa: E402
from schemas import ChecklistItem, FindingStatus, Severity  # noqa: E402


# --- Offline helpers --------------------------------------------------------


class _FakeToolBlock:
    type = "tool_use"

    def __init__(self, payload: dict) -> None:
        self.input = payload


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.content = [_FakeToolBlock(payload)]


def _make_chunks(n: int) -> list:
    pdf = _make_pdf([[("Heading", 24), (f"Body para {i}.", 11)] for i in range(n)])
    return extract_pdf_with_metadata_from_bytes(pdf)


def _make_pdf(pages: list[list[tuple[str, float]]]) -> bytes:
    doc = fitz.open()
    for page_lines in pages:
        page = doc.new_page()
        y = 50.0
        for text, size in page_lines:
            page.insert_text((50, y), text, fontsize=size)
            y += size * 1.5
    data = doc.tobytes()
    doc.close()
    return data


def _item() -> ChecklistItem:
    return ChecklistItem(id="t1", title="Test", description="Test item.", severity=Severity.HIGH)


# --- Offline tests ----------------------------------------------------------


def test_load_checklist_known_ids() -> None:
    for cid in ("soc2_trust_services", "esg_basic", "code_review_security"):
        items = load_checklist(cid)
        assert len(items) == 3, f"{cid}: expected 3 items, got {len(items)}"
        assert all(isinstance(it.id, str) and it.id for it in items)


def test_load_checklist_unknown_raises() -> None:
    try:
        load_checklist("nonexistent")
    except ValueError:
        return
    raise AssertionError("expected ValueError on unknown checklist_id")


def test_parse_tool_response_pass_with_citations() -> None:
    chunks = _make_chunks(3)
    response = _FakeResponse(
        {
            "status": "PASS",
            "severity": "HIGH",
            "description": "Document covers the requirement.",
            "supporting_chunk_ids": [0, 2],
            "confidence": 0.9,
        }
    )
    finding = _parse_tool_response(response, _item(), chunks)
    assert finding.status == FindingStatus.PASS
    assert len(finding.supporting_chunks) == 2
    assert finding.confidence == 0.9


def test_parse_tool_response_fail_without_citations_downgrades() -> None:
    """Citations-mandatory rule: FAIL without supporting_chunks → PARTIAL."""
    chunks = _make_chunks(3)
    response = _FakeResponse(
        {
            "status": "FAIL",
            "severity": "CRITICAL",
            "description": "Model claims violation but cites nothing.",
            "supporting_chunk_ids": [],
            "confidence": 0.6,
        }
    )
    finding = _parse_tool_response(response, _item(), chunks)
    assert finding.status == FindingStatus.PARTIAL, (
        f"FAIL with no citations should downgrade to PARTIAL, got {finding.status}"
    )
    assert finding.supporting_chunks == []


def test_parse_tool_response_drops_out_of_range_indices() -> None:
    chunks = _make_chunks(2)
    response = _FakeResponse(
        {
            "status": "PASS",
            "severity": "LOW",
            "description": "Hallucinated index 99 should be dropped.",
            "supporting_chunk_ids": [0, 99, 1, -1],
            "confidence": 0.8,
        }
    )
    finding = _parse_tool_response(response, _item(), chunks)
    assert len(finding.supporting_chunks) == 2, "out-of-range indices must be filtered"


def test_parse_tool_response_no_tool_block_raises() -> None:
    """If the model returns text instead of a tool call, parsing must raise."""

    class _TextOnly:
        content = [type("X", (), {"type": "text", "text": "no tool call"})()]

    try:
        _parse_tool_response(_TextOnly(), _item(), _make_chunks(1))
    except ValueError:
        return
    raise AssertionError("expected ValueError when no tool_use block is present")


# --- Live-API test (skipped without a real key) -----------------------------


def _has_real_key() -> bool:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    return bool(key) and not key.startswith("sk-ant-PLACEHOLDER")


def test_live_evaluate_checklist_soc2() -> None:
    if not _has_real_key():
        print("    (skipped — no real ANTHROPIC_API_KEY)")
        return

    # Build a small synthetic SOC2-flavored PDF with mixed signals so all three
    # SOC2 items have something to chew on.
    pdf = _make_pdf(
        [
            [
                ("Access Controls", 24),
                ("All users authenticate via Okta SSO with TOTP MFA enforced.", 11),
            ],
            [
                ("Encryption", 24),
                ("All data in transit uses TLS 1.3. Internal services use mTLS.", 11),
            ],
            [
                ("Audit Logging", 24),
                ("Authentication events are logged but retention policy is not documented.", 11),
            ],
        ]
    )
    chunks = extract_pdf_with_metadata_from_bytes(pdf)
    assert len(chunks) >= 3, f"expected >=3 chunks from synth PDF, got {len(chunks)}"

    t0 = time.perf_counter()
    result = asyncio.run(
        evaluate_checklist(
            document_id="test-doc",
            checklist_id="soc2_trust_services",
            chunks=chunks,
        )
    )
    elapsed = time.perf_counter() - t0

    assert result.status.value == "completed", f"expected completed, got {result.status}"
    assert len(result.findings) == 3, f"expected 3 findings, got {len(result.findings)}"
    for f in result.findings:
        if f.status == FindingStatus.FAIL:
            assert f.supporting_chunks, f"FAIL finding {f.item_id} has no citations"
        for c in f.supporting_chunks:
            assert c.page >= 1, f"citation page must be 1-indexed (got {c.page})"
    assert elapsed < 120, f"evaluation took {elapsed:.1f}s, expected <120s"
    print(f"    live: {len(result.findings)} findings · {elapsed:.1f}s · summary={result.summary!r}")


# --- Runner -----------------------------------------------------------------


TESTS = [
    test_load_checklist_known_ids,
    test_load_checklist_unknown_raises,
    test_parse_tool_response_pass_with_citations,
    test_parse_tool_response_fail_without_citations_downgrades,
    test_parse_tool_response_drops_out_of_range_indices,
    test_parse_tool_response_no_tool_block_raises,
    test_live_evaluate_checklist_soc2,
]


def main() -> int:
    failures: list[tuple[str, str]] = []
    for fn in TESTS:
        try:
            fn()
            print(f"  ok  {fn.__name__}")
        except Exception:
            print(f"  FAIL {fn.__name__}")
            failures.append((fn.__name__, traceback.format_exc()))

    if failures:
        print("")
        for name, tb in failures:
            print(f"--- {name} ---")
            print(tb)
        print(f"FAILED — {len(failures)}/{len(TESTS)} test(s) failed")
        return 1

    suffix = " (live test ran)" if _has_real_key() else " (live test skipped)"
    print(f"OK — {len(TESTS)}/{len(TESTS)} tests passed{suffix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
