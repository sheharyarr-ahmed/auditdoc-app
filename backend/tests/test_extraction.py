"""Tests for extraction.py — synthesizes PDFs with PyMuPDF, no external assets.

Run from backend/ directory:
    .venv/bin/python -m tests.test_extraction
"""

from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

# Allow `python -m tests.test_extraction` from the backend/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fitz  # noqa: E402

from extraction import extract_pdf_with_metadata_from_bytes  # noqa: E402


def _make_pdf(pages: list[list[tuple[str, float]]]) -> bytes:
    """Build an in-memory PDF.

    `pages` = list of pages, each = list of (text, font_size) tuples drawn
    top-to-bottom on that page. An empty list = a blank page.
    """
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


def test_basic_extraction() -> None:
    pdf = _make_pdf(
        [
            [("First page body text.", 11)],
            [("Second page body text.", 11)],
            [("Third page body text.", 11)],
        ]
    )
    chunks = extract_pdf_with_metadata_from_bytes(pdf)
    assert len(chunks) >= 3, f"expected >=3 chunks, got {len(chunks)}"
    pages_seen = {c.page for c in chunks}
    assert pages_seen == {1, 2, 3}, f"expected pages {{1,2,3}}, got {pages_seen}"
    assert chunks[0].page == 1, "first chunk must be page 1, not 0 (1-indexed)"


def test_section_detection() -> None:
    pdf = _make_pdf(
        [
            [
                ("Access Controls", 24),  # heading
                ("Users authenticate via SSO.", 11),  # body
            ]
        ]
    )
    chunks = extract_pdf_with_metadata_from_bytes(pdf)
    assert len(chunks) == 1, f"expected 1 body chunk, got {len(chunks)} ({[c.text for c in chunks]})"
    body = chunks[0]
    assert body.section == "Access Controls", f"expected section 'Access Controls', got {body.section!r}"
    assert "SSO" in body.text


def test_section_carries_across_pages() -> None:
    pdf = _make_pdf(
        [
            [("Encryption", 24), ("Data at rest is AES-256.", 11)],
            [("Keys rotate every 90 days.", 11)],  # no heading on page 2
        ]
    )
    chunks = extract_pdf_with_metadata_from_bytes(pdf)
    page2_chunks = [c for c in chunks if c.page == 2]
    assert page2_chunks, "expected at least one chunk on page 2"
    assert page2_chunks[0].section == "Encryption", (
        f"section should carry across pages; page-2 section was {page2_chunks[0].section!r}"
    )


def test_corrupt_bytes_raises() -> None:
    try:
        extract_pdf_with_metadata_from_bytes(b"this is not a pdf at all")
    except ValueError:
        return  # expected
    except Exception as exc:
        raise AssertionError(f"expected ValueError, got {type(exc).__name__}: {exc}") from exc
    raise AssertionError("expected ValueError, but no exception was raised")


def test_empty_bytes_raises() -> None:
    try:
        extract_pdf_with_metadata_from_bytes(b"")
    except ValueError:
        return
    raise AssertionError("expected ValueError on empty bytes")


def test_performance_20_pages() -> None:
    pdf = _make_pdf(
        [[("Section " + str(i), 24), ("Body paragraph " + str(i) + " " * 50, 11)] for i in range(20)]
    )
    t0 = time.perf_counter()
    chunks = extract_pdf_with_metadata_from_bytes(pdf)
    elapsed = time.perf_counter() - t0
    assert elapsed < 5.0, f"20-page extract took {elapsed:.2f}s, expected <5s"
    assert len(chunks) >= 20, f"expected >=20 chunks across 20 pages, got {len(chunks)}"


def test_blank_page_skipped() -> None:
    pdf = _make_pdf(
        [
            [],  # blank
            [("Body text on page 2.", 11)],
        ]
    )
    chunks = extract_pdf_with_metadata_from_bytes(pdf)
    pages_seen = {c.page for c in chunks}
    assert 1 not in pages_seen, "blank page 1 should produce no chunks"
    assert 2 in pages_seen, "page 2 should produce at least one chunk"


TESTS = [
    test_basic_extraction,
    test_section_detection,
    test_section_carries_across_pages,
    test_corrupt_bytes_raises,
    test_empty_bytes_raises,
    test_performance_20_pages,
    test_blank_page_skipped,
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

    print(f"OK — {len(TESTS)}/{len(TESTS)} tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
