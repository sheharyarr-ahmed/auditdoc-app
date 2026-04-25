# Extraction Agent — Task 1.1

**Goal:** Implement `backend/extraction.py` so that uploaded PDFs become a list of `Chunk` objects with page + section metadata.

## Inputs
- `extract_pdf_with_metadata(file_path: str) -> list[Chunk]`
- `extract_pdf_with_metadata_from_bytes(data: bytes) -> list[Chunk]`

## Output contract
Each `Chunk` must have:
- `page` — 1-indexed (PyMuPDF is 0-indexed; add 1)
- `section` — heading text if detected via font-size heuristic, else `"body"`
- `text` — block-level text (use `page.get_text("blocks")`)
- `metadata` — at minimum `{"bbox": "x0,y0,x1,y1", "font_size": float}`

## Acceptance (TASK_BREAKDOWN.md §1.1)
- 10–20 page PDF extracts in < 5s
- Corrupt PDFs return a clear `ValueError`, never crash
- 1-indexed pages — verified by test
- INFO-level logging at start and end with document id

## Reference
- Code patterns: `.claude/skills/pdf-extraction.md`
- Constraints: root CLAUDE.md §CRITICAL CONSTRAINTS #4
