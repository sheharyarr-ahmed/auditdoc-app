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
- [x] 3.1 — Backend on Vercel (Python Fluid Compute) — completed 2026-04-25 · live at https://auditdoc-backend.vercel.app · pivoted from Render to avoid card-on-file requirement · zero-config FastAPI auto-detection (no api/index.py wrapper or vercel.json needed) · linked via `vercel link --yes`, env vars set via `vercel env add`, deployed via `vercel deploy --prod --yes`
- [x] 3.2 — Frontend on Vercel — completed 2026-04-25 · live at https://auditdoc.vercel.app · separate Vercel project (auditdoc-frontend), rootDir=frontend, BACKEND_URL set via `vercel env add` to the backend URL
- [x] 3.3 — End-to-end production test — completed 2026-04-25 · `/api/upload` → `/api/evaluate` → `/api/results/[id]` round-trip via prod frontend returns same 3-finding SOC2 shape as local: PARTIAL/HIGH (2 cites), PASS/HIGH (1 cite), PARTIAL/MEDIUM (1 cite). Backend CORS tightened from `*` to the frontend URL.

## Follow-ups
- Next.js 14.1.0 has a known security CVE (flagged in Vercel build log, see https://nextjs.org/blog/security-update-2025-12-11). Bump to a 14.x patch release at next opportunity.

## Decisions log
- 2026-04-25 — LLM is Anthropic Claude 4.x via `anthropic` SDK; env var named `ANTHROPIC_API_KEY` (not `OPENAI_API_KEY` as in the original draft).
- 2026-04-25 — `extraction.py` and `evaluation.py` ship as `NotImplementedError` stubs after initial scaffold.
