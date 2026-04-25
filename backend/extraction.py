"""PDF extraction with page + section metadata.

See `.claude/skills/pdf-extraction.md` for the patterns this implements and
`.claude/agents/extraction-agent.md` for the task spec.
"""

from __future__ import annotations

import logging
from typing import Any

import fitz  # PyMuPDF

from schemas import Chunk

logger = logging.getLogger(__name__)

MAX_PAGES_WARN = 500
HEADING_RATIO = 1.2  # block dominant size >= modal * ratio → treat as heading
MAX_HEADING_LEN = 200  # block this long can't be a heading


def _modal_font_size(page_dict: dict[str, Any]) -> float:
    """Return the dominant font size on a page, weighted by character count.

    A long body paragraph at 11pt outvotes a short heading at 24pt — exactly
    what we want, since the heading-detection step compares against this.
    """
    weights: dict[float, int] = {}
    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                size = round(float(span.get("size", 0.0)), 1)
                if size > 0:
                    weights[size] = weights.get(size, 0) + len(span.get("text", ""))
    if not weights:
        return 0.0
    return max(weights.items(), key=lambda kv: kv[1])[0]


def _block_dominant_font_size(block: dict[str, Any]) -> float:
    """Largest span size in a block — the candidate for heading detection."""
    sizes: list[float] = []
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            sizes.append(float(span.get("size", 0.0)))
    return max(sizes) if sizes else 0.0


def _block_text(block: dict[str, Any]) -> str:
    """Concatenate spans into one string per block, preserving line breaks."""
    parts: list[str] = []
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            parts.append(span.get("text", ""))
        parts.append("\n")
    return "".join(parts).strip()


def extract_pdf_with_metadata_from_bytes(data: bytes) -> list[Chunk]:
    """Extract a PDF (in-memory bytes) into a list of Chunk objects.

    Each Chunk carries:
      - page (1-indexed)
      - section (last seen heading on or before this block, "body" if none)
      - text (block-level)
      - metadata: {"bbox": "x0,y0,x1,y1", "font_size": <dominant span size>}

    Raises ValueError on empty / corrupt input. Caller (main.py) maps that to HTTP 400.
    """
    if not data:
        raise ValueError("Empty PDF bytes")

    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        # Don't leak full traceback to callers — see rules/error-handling.md.
        raise ValueError(f"Could not open PDF: {type(exc).__name__}") from exc

    chunks: list[Chunk] = []
    try:
        page_count = doc.page_count
        if page_count > MAX_PAGES_WARN:
            logger.warning("PDF has %d pages, exceeds soft limit of %d", page_count, MAX_PAGES_WARN)

        logger.info("extract: starting page_count=%d", page_count)

        current_section = "body"
        for page_index in range(page_count):
            page = doc.load_page(page_index)
            page_dict = page.get_text("dict")

            body_size = _modal_font_size(page_dict)
            if body_size == 0.0:
                # Image-only or blank page — nothing to extract.
                continue

            for block in page_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue
                text = _block_text(block)
                if not text:
                    continue

                dominant = _block_dominant_font_size(block)
                if dominant >= body_size * HEADING_RATIO and len(text) < MAX_HEADING_LEN:
                    current_section = text.replace("\n", " ").strip()
                    continue  # heading itself is metadata, not a chunk

                bbox = block.get("bbox", (0.0, 0.0, 0.0, 0.0))
                chunks.append(
                    Chunk(
                        page=page_index + 1,  # 1-indexed — see rules/citations-mandatory.md
                        section=current_section,
                        text=text,
                        metadata={
                            "bbox": f"{bbox[0]:.1f},{bbox[1]:.1f},{bbox[2]:.1f},{bbox[3]:.1f}",
                            "font_size": float(dominant),
                        },
                    )
                )
    finally:
        doc.close()

    logger.info("extract: done chunks=%d", len(chunks))
    return chunks


def extract_pdf_with_metadata(file_path: str) -> list[Chunk]:
    """Disk-path wrapper around `extract_pdf_with_metadata_from_bytes`."""
    try:
        with open(file_path, "rb") as f:
            data = f.read()
    except OSError as exc:
        raise ValueError(f"Could not read PDF file: {type(exc).__name__}") from exc
    return extract_pdf_with_metadata_from_bytes(data)
