# Evaluation Agent — Task 1.2

**Goal:** Implement `backend/evaluation.py` to evaluate a checklist against extracted chunks using Claude with structured output.

## Functions to implement
- `load_checklist(checklist_id: str) -> list[ChecklistItem]`
- `async evaluate_single_item(item, chunks, *, timeout_s=30) -> Finding`
- `async evaluate_checklist(document_id, checklist_id, chunks, *, overall_timeout_s=120) -> EvaluationResult`

## Hard rules
1. Every `FAIL` finding **must** have at least one `supporting_chunk` with a real page number from `chunks`. If the model can't cite, downgrade to `PARTIAL`.
2. Use the `anthropic` Python SDK with tool-use / structured-output to force a JSON-shaped response matching `Finding`.
3. Default model: `claude-sonnet-4-6`. Escalate to `claude-opus-4-7` only for items the spec marks as "complex".
4. Per-item timeout 30s, overall 120s. On timeout, raise `TimeoutError` from `main.py`'s perspective (or set status `FAILED` in the aggregate).
5. Never log full document content — only token counts, item id, duration, status.

## Reference
- `.claude/skills/claude-structured-output.md`
- `.claude/rules/citations-mandatory.md`
- `.claude/rules/error-handling.md`
- Root CLAUDE.md §CRITICAL CONSTRAINTS #1, #5
