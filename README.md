# AuditDoc

Compliance document intelligence — upload a PDF, pick a checklist, get findings with mandatory page citations in ~5 seconds. FastAPI + PyMuPDF on the backend, Next.js 14 on the frontend, Anthropic Claude (Sonnet 4.6 default) for evaluation.

The full spec lives in [`CLAUDE.md`](./CLAUDE.md). Build status, decisions, and per-task notes live in [`.claude/memory/MEMORY.md`](./.claude/memory/MEMORY.md).

## Repository layout

```
auditdoc-project/
├── backend/                # FastAPI app — extraction.py, evaluation.py, schemas.py, main.py
│   ├── tests/              # standalone runners (no pytest dep)
│   ├── runtime.txt         # Python version pin for Render
│   └── requirements.txt
├── frontend/               # Next.js 14 App Router
│   ├── app/                # page.tsx + /api/{upload,evaluate,results/[id]} proxy routes
│   ├── components/         # 6 components (UploadZone, ChecklistSelector, FindingCard, …)
│   └── lib/types.ts        # mirrors backend/schemas.py
├── .claude/                # project bible, agents, skills, rules, MEMORY
├── render.yaml             # backend deploy spec
├── .env.template           # copy → .env.local for local dev
└── CLAUDE.md
```

## Local development

Prereqs: Python 3.13, Node 20+, an Anthropic API key.

```bash
# 1. Backend deps
cd backend
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Frontend deps
cd ../frontend
npm install

# 3. Env
cd ..
cp .env.template .env.local
# edit .env.local — set ANTHROPIC_API_KEY=sk-ant-…
```

Run two terminals:

```bash
# Terminal A — backend on :8000
cd backend && .venv/bin/uvicorn main:app --port 8000 --reload

# Terminal B — frontend on :3000
cd frontend && npm run dev
```

Open http://localhost:3000.

## Backend tests

Self-contained runners — no pytest. Live tests skip automatically when `ANTHROPIC_API_KEY` is the placeholder.

```bash
cd backend
.venv/bin/python -m tests.test_extraction   # 7 tests, no API
.venv/bin/python -m tests.test_evaluation   # 6 offline + 1 live
.venv/bin/python -m tests.test_acceptance   # boots uvicorn, exercises every endpoint
```

## Deployment

The backend deploys to Render, the frontend to Vercel. Both pull from the same GitHub repo.

### 1. Backend → Render

The repo includes [`render.yaml`](./render.yaml) — Render's blueprint format. Two ways to deploy:

**Option A — Blueprint (recommended)**
1. In Render dashboard → **New** → **Blueprint** → connect your GitHub repo.
2. Render reads `render.yaml`, creates the `auditdoc-backend` web service.
3. Set the two env vars marked `sync: false` in the dashboard:
   - `ANTHROPIC_API_KEY` — your Anthropic key.
   - `ALLOWED_ORIGINS` — your Vercel production URL (set after step 2). For the first deploy you can use `*` or a placeholder; tighten after the frontend has a URL.
4. Render builds (~2 min for first deploy), deploys, and exposes a URL like `https://auditdoc-backend.onrender.com`.
5. Smoke check: `curl https://auditdoc-backend.onrender.com/health` → `{"status":"ok"}`.

**Option B — Manual web service**
- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 2`
- Health check path: `/health`
- Env vars: `ANTHROPIC_API_KEY`, `ALLOWED_ORIGINS`, `LOG_LEVEL=INFO`, `MAX_UPLOAD_BYTES=52428800`, `PYTHON_VERSION=3.13.13`

**Free-tier note:** Render's free plan sleeps the service after 15 min of inactivity. The first request after sleep takes ~30–50s. For a portfolio demo this is acceptable; bump `plan: starter` → `standard` in `render.yaml` for always-on.

### 2. Frontend → Vercel

The frontend is a standard Next.js 14 App Router project — no custom config needed.

1. In Vercel dashboard → **Add New** → **Project** → import the GitHub repo.
2. **Root Directory: `frontend`** (this is the only non-default setting).
3. Framework preset auto-detects as Next.js. Build command and output directory leave as default.
4. Environment Variables (production scope):
   - `BACKEND_URL` — the Render URL from step 1, e.g. `https://auditdoc-backend.onrender.com`.
   - `ANTHROPIC_API_KEY` — **not needed**. The frontend never talks to Anthropic directly; calls go through the backend.
5. Deploy. Vercel issues a URL like `https://auditdoc.vercel.app`.

### 3. Tighten CORS

Once the Vercel URL is known, go back to Render → service → Environment, and set:
```
ALLOWED_ORIGINS=https://auditdoc.vercel.app
```
Render will redeploy automatically. From now on only your Vercel domain can call the backend.

### 4. End-to-end smoke

```bash
# Upload a real PDF via your live frontend
curl -F "file=@some.pdf" https://auditdoc.vercel.app/api/upload
# Use the returned document_id
curl -X POST https://auditdoc.vercel.app/api/evaluate \
  -H 'content-type: application/json' \
  -d '{"document_id":"<id>","checklist_id":"soc2_trust_services"}'
```

Or just open the Vercel URL in a browser and use it.

## Environment variables — full matrix

| Var | Where set | Used by | Notes |
|-----|-----------|---------|-------|
| `ANTHROPIC_API_KEY` | local: `.env.local`; prod: Render dashboard | `backend/evaluation.py` | Never committed. |
| `BACKEND_URL` | local: `.env.local`; prod: Vercel dashboard | `frontend/app/api/*/route.ts` | Local default `http://localhost:8000`. Prod = Render service URL. |
| `ALLOWED_ORIGINS` | local: `.env.local`; prod: Render dashboard | `backend/main.py` (CORS) | Comma-separated. Local = `http://localhost:3000`. Prod = Vercel URL. |
| `LOG_LEVEL` | both | `backend/main.py` | `INFO` for prod, `DEBUG` only when troubleshooting. |
| `MAX_UPLOAD_BYTES` | both (optional) | `backend/main.py` | Default 52428800 (50MB). Lower in tests. |
| `NEXT_PUBLIC_API_URL` | legacy | unused | Stays in `.env.template` for compatibility but isn't read anywhere now that the frontend uses relative `/api/*`. Can be removed. |

## Architectural decisions

- **Citations are mandatory.** A `Finding` with `status=FAIL` and no `supporting_chunks` is auto-downgraded to `PARTIAL`. See [`.claude/rules/citations-mandatory.md`](./.claude/rules/citations-mandatory.md).
- **Font-size based section detection.** Char-count-weighted modal page font; blocks ≥ 1.2× modal are treated as headings. See [`.claude/skills/pdf-extraction.md`](./.claude/skills/pdf-extraction.md).
- **Tool-use forced output.** Evaluation calls Claude with a `record_finding` tool and `tool_choice` set to that tool, forcing strict-JSON output. See [`.claude/skills/claude-structured-output.md`](./.claude/skills/claude-structured-output.md).
- **Concurrency.** `evaluate_checklist` runs items in parallel under `Semaphore(4)`; per-item timeout 30s, overall 120s.
- **Stateless backend.** Documents and evaluations live in process-memory dicts. They're lost on restart. Move to Supabase in the post-MVP phase.

## License

(Add a license here when ready — e.g. MIT.)
