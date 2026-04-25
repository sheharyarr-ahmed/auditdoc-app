# Skill — FastAPI async routes

```python
from fastapi import FastAPI, HTTPException, UploadFile, File

@app.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)) -> UploadResponse:
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="too large")
    if not contents.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="not a PDF")
    ...
```

## Conventions
- Always declare `response_model=` so OpenAPI + serialization line up.
- Return Pydantic models, not dicts (FastAPI serializes them properly).
- Use `HTTPException` with explicit status codes — never `500` as a default.
- Use `async def` everywhere; it makes I/O concurrency free.
- Validate at the boundary (file size, magic bytes) before allocating large objects.
- Wrap external calls (PyMuPDF, Anthropic) in try/except and translate exceptions to HTTPExceptions.
