# Skill — PDF Extraction with PyMuPDF

Font-size based section detection. The implementation lives in
`backend/extraction.py`; this file is the canonical pattern reference.

```python
import fitz  # PyMuPDF
from schemas import Chunk

HEADING_RATIO = 1.2          # block dominant size >= modal * ratio → heading
MAX_HEADING_LEN = 200        # block this long can't plausibly be a heading


def _modal_font_size(page_dict) -> float:
    """Char-count-weighted modal size on a page → 'body' size for that page.

    Weighting matters: a 200-char body paragraph at 11pt outvotes a 20-char
    heading at 24pt. Without the weight, single-line body pages with a long
    title would get the title classified as body.
    """
    weights = {}
    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:  # 0 == text
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                size = round(float(span.get("size", 0.0)), 1)
                if size > 0:
                    weights[size] = weights.get(size, 0) + len(span.get("text", ""))
    return max(weights.items(), key=lambda kv: kv[1])[0] if weights else 0.0


def _block_dominant_font_size(block) -> float:
    sizes = [float(s.get("size", 0.0)) for line in block.get("lines", []) for s in line.get("spans", [])]
    return max(sizes) if sizes else 0.0


def extract_pdf_with_metadata_from_bytes(data: bytes) -> list[Chunk]:
    if not data:
        raise ValueError("Empty PDF bytes")
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Could not open PDF: {type(exc).__name__}") from exc

    chunks: list[Chunk] = []
    try:
        current_section = "body"
        for page_index in range(doc.page_count):
            page_dict = doc.load_page(page_index).get_text("dict")
            body_size = _modal_font_size(page_dict)
            if body_size == 0.0:
                continue  # blank / image-only page
            for block in page_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue
                text = _block_text(block)  # joins spans, strips
                if not text:
                    continue
                dominant = _block_dominant_font_size(block)
                if dominant >= body_size * HEADING_RATIO and len(text) < MAX_HEADING_LEN:
                    current_section = text.replace("\n", " ").strip()
                    continue  # heading isn't itself a chunk
                bbox = block.get("bbox", (0, 0, 0, 0))
                chunks.append(Chunk(
                    page=page_index + 1,  # 1-INDEXED
                    section=current_section,
                    text=text,
                    metadata={
                        "bbox": f"{bbox[0]:.1f},{bbox[1]:.1f},{bbox[2]:.1f},{bbox[3]:.1f}",
                        "font_size": float(dominant),
                    },
                ))
    finally:
        doc.close()
    return chunks
```

## Pitfalls

- **PyMuPDF pages are 0-indexed.** Always `+1` before storing on a `Chunk`. The
  citation rule depends on this — auditors clicking a page-3 citation must land
  on page 3, not page 2.
- **`fitz.open(stream=...)` requires `filetype="pdf"`** for in-memory bytes.
  Without it, PyMuPDF raises a non-obvious error.
- **Empty-text blocks happen on image-heavy pages.** `_block_text` will return
  `""` for them; skip with `if not text: continue`.
- **`with fitz.open(...)` releases native handles**, but using a `try/finally`
  with explicit `doc.close()` is equally safe and slightly more explicit when
  control flow is non-trivial. Don't leak by skipping either form.
- **Section heuristic is fragile on multi-column layouts** (PyMuPDF reads
  blocks in source order, which may not match visual reading order). Acceptable
  for MVP; switch to `page.get_text("blocks", sort=True)` + reading-order
  inference if it bites us.
- **Don't rely on `block_no`** for ordering — different PDFs use different
  conventions. Iteration order of `page_dict["blocks"]` is the PyMuPDF default
  and is what we use.
