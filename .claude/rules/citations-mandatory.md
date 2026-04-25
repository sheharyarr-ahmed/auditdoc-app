# Rule — Citations are mandatory

## The rule
A `Finding` with `status == FAIL` **must** have `len(supporting_chunks) >= 1`. Each chunk must reference a real `page` and `text` excerpt drawn from the extracted document, not synthesized.

## Why
Hallucinated citations are the failure mode that breaks compliance evaluation entirely — auditors lose trust the moment they click through to a page that doesn't say what the model claimed. AuditDoc's pitch is "zero hallucinated citations." This rule is the hard floor that lets us make that promise.

## Enforcement (defense in depth)

1. **Schema-level (`schemas.py`)** — `Finding` has a `field_validator` that raises `ValueError` if `status == FAIL` and `supporting_chunks` is empty.
2. **Evaluation-level (`evaluation.py`)** — after parsing the LLM response, if `status == FAIL` and `supporting_chunks` is empty, **downgrade** the status to `PARTIAL` rather than raising. This keeps the evaluation moving but signals lower confidence.
3. **Prompt-level (`skills/claude-structured-output.md`)** — the tool schema describes `supporting_chunk_ids` as required and tells the model to use `NOT_APPLICABLE` if it can't cite.
4. **Index validation** — bounds-check every `supporting_chunk_ids` against `len(chunks)`. The model can hallucinate indices.

## What this rule is *not*
- It does not require citations on `PASS`, `PARTIAL`, or `NOT_APPLICABLE` findings (though they're encouraged for `PASS`).
- It does not enforce a minimum citation count beyond 1.
