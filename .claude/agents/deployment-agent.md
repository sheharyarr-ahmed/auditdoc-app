# Deployment Agent — Tasks 3.1 / 3.2 / 3.3

## Backend → Render (Task 3.1)
- Service type: Web Service, Python 3.11+
- Build: `pip install -r backend/requirements.txt`
- Start: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`
- Env vars: `ANTHROPIC_API_KEY`, `LOG_LEVEL=INFO`
- Verify: `curl https://<service>.onrender.com/health` → 200

## Frontend → Vercel (Task 3.2)
- Framework preset: Next.js 14 (App Router)
- Root directory: `frontend`
- Env: `NEXT_PUBLIC_API_URL=https://<render-service>.onrender.com`
- Verify: load homepage, no console errors

## End-to-end (Task 3.3)
- Upload sample PDF via Vercel URL → expect `document_id`
- Evaluate against `soc2_trust_services` → expect findings with citations
- Try a 60MB file → expect 413
- Try a `.txt` rename to `.pdf` → expect 400 (magic-byte check)
