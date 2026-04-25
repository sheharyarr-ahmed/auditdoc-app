# Skill — Pydantic v2 patterns

```python
from pydantic import BaseModel, Field, field_validator

class Finding(BaseModel):
    item_id: str
    status: FindingStatus
    severity: Severity
    description: str
    supporting_chunks: list[Chunk] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("supporting_chunks")
    @classmethod
    def _fail_requires_citation(cls, v, info):
        if info.data.get("status") == FindingStatus.FAIL and not v:
            raise ValueError("FAIL findings must include at least one supporting_chunk")
        return v
```

## Conventions
- All enums are `str, Enum` so JSON round-trips cleanly.
- Use `Field(..., description=...)` for anything user-facing — surfaces in OpenAPI docs.
- Prefer `field_validator` over `model_validator` for single-field rules.
- `model_dump(mode="json")` when constructing `JSONResponse` so datetimes serialize.
- Never use `Any`. If a value is genuinely polymorphic, type it as `str | int | float | bool`.
