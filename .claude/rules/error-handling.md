# Rule — Error handling is explicit

## Status code matrix

| Situation | Code |
|-----------|------|
| Bad request body, invalid PDF magic, empty file | 400 |
| document_id / evaluation_id not found | 404 |
| File > 50MB | 413 |
| Rate-limited (per-user) | 429 |
| LLM / extraction timeout | 503 |
| Anything else (use sparingly) | 500 |

## Required pattern

```python
try:
    result = await do_thing(...)
except TimeoutError:
    raise HTTPException(status_code=503, detail="upstream timeout")
except ValueError as exc:
    raise HTTPException(status_code=400, detail=str(exc))
except Exception as exc:
    logger.error("do_thing failed: %s", type(exc).__name__)  # type only — no full traceback to logs
    raise HTTPException(status_code=500, detail="internal error")
```

## Forbidden
- Returning raw exception strings to the client.
- Logging full document content, full prompts, or API keys.
- `except Exception` with no logging.
- Swallowing exceptions silently.

## Why
Exposing tracebacks leaks implementation details and sometimes secrets. Specific status codes let the frontend present accurate error UX.
