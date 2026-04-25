# AuditDoc — Session Progress

Update this file as TASK_BREAKDOWN.md tasks are completed. Keep it short and skimmable.

## Phase 1 — Backend
- [x] 1.1 — extraction.py (PyMuPDF) — completed 2026-04-25 · 7/7 unit tests pass · /upload + /evaluate round-trip works (evaluation falls through to Task 1.2 stub as designed)
- [x] 1.2 — evaluation.py (Claude tool-use) — completed 2026-04-25 · Sonnet 4.6 default · Semaphore(4) · 7/7 unit + live tests pass · live SOC2 eval ~4.6s for 3 items · /upload + /evaluate end-to-end returns real findings with mandatory page citations
- [x] 1.3 — Local backend smoke test — completed 2026-04-25 · `tests/test_acceptance.py` boots uvicorn in subprocess, covers /health + /upload (happy/empty/non-PDF/413) + /evaluate (404/400/live) + /results (404/live) + log hygiene (no key leak, no traceback). Full suite: 7+7+1 passing, including live SOC2 round-trip.

## Phase 2 — Frontend
- [x] 2.1 — React components — completed 2026-04-25 · 6 components in `frontend/components/` (UploadZone with HTML5 drag-and-drop, ChecklistSelector, ProgressBar indeterminate, ErrorAlert, FindingCard, ResultsDisplay) · severity styling moved into FindingCard
- [x] 2.2 — API routes split — completed 2026-04-25 · `app/api/upload`, `app/api/evaluate` (`maxDuration=180`), `app/api/results/[id]` · all proxy to `BACKEND_URL` · placeholder `app/api/route.ts` deleted
- [x] 2.3 — Local frontend smoke — completed 2026-04-25 · `tsc --noEmit` clean · `next build` clean (3 dynamic API routes registered) · live round-trip via Next proxy reproduced Phase-1 SOC2 finding shape

## Phase 3 — Deployment
- [~] 3.1 — Backend on Render — configs ready (`render.yaml`, `runtime.txt`, env-driven CORS via `ALLOWED_ORIGINS`); awaiting user to push repo + connect Render dashboard
- [~] 3.2 — Frontend on Vercel — no custom config needed; user sets root dir = `frontend` + `BACKEND_URL` env var in Vercel dashboard
- [ ] 3.3 — End-to-end production test — pending live URLs

## Decisions log
- 2026-04-25 — LLM is Anthropic Claude 4.x via `anthropic` SDK; env var named `ANTHROPIC_API_KEY` (not `OPENAI_API_KEY` as in the original draft).
- 2026-04-25 — `extraction.py` and `evaluation.py` ship as `NotImplementedError` stubs after initial scaffold.
