# Skill — Claude structured output (tool use)

Use the `anthropic` SDK's tool-use mechanism to force the model into a JSON shape that matches `Finding`. Tool use is the most reliable way to get strict JSON out of Claude 4.x.

## Default model

```python
DEFAULT_MODEL = "claude-sonnet-4-6"  # Sonnet 4.6 = good cost/quality for evals
HARD_MODEL = "claude-opus-4-7"        # Reserve for items flagged "complex"
```

## Tool schema for a Finding

```python
finding_tool = {
    "name": "record_finding",
    "description": "Record an audit finding for a single checklist item.",
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["PASS", "FAIL", "PARTIAL", "NOT_APPLICABLE"]},
            "severity": {"type": "string", "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"]},
            "description": {"type": "string"},
            "supporting_chunk_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Indices into the chunks list. Use [] only if NOT_APPLICABLE.",
            },
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
        "required": ["status", "severity", "description", "supporting_chunk_ids", "confidence"],
    },
}
```

## Call pattern

```python
from anthropic import AsyncAnthropic

client = AsyncAnthropic()  # reads ANTHROPIC_API_KEY

response = await client.messages.create(
    model=DEFAULT_MODEL,
    max_tokens=1024,
    tools=[finding_tool],
    tool_choice={"type": "tool", "name": "record_finding"},
    messages=[
        {"role": "user", "content": _build_prompt(item, chunks)},
    ],
)
tool_block = next(b for b in response.content if b.type == "tool_use")
data = tool_block.input  # dict matching the schema
```

## Mapping back to `Finding`

```python
finding = Finding(
    item_id=item.id,
    status=FindingStatus(data["status"]),
    severity=Severity(data["severity"]),
    description=data["description"],
    supporting_chunks=[chunks[i] for i in data["supporting_chunk_ids"] if 0 <= i < len(chunks)],
    confidence=float(data["confidence"]),
)
# Citations rule: downgrade FAIL → PARTIAL if no chunks
if finding.status == FindingStatus.FAIL and not finding.supporting_chunks:
    finding = finding.model_copy(update={"status": FindingStatus.PARTIAL})
```

## Pitfalls
- `tool_choice` must specify the tool by name to force JSON output.
- The model may hallucinate chunk indices > `len(chunks)` — always bounds-check.
- Don't put the entire PDF in the prompt — chunk it first, send only relevant excerpts.
