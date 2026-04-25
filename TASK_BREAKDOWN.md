# 🎯 AUDITDOC BUILD CHECKLIST FOR CLAUDE CODE

**Status:** Ready to build
**Estimated Time:** 6-8 hours with Claude Code
**Priority:** MVP launch (JOB #12 Kuwait + Upwork pipeline)

---

## PHASE 1: Backend Implementation (3-4 hours)

### Task 1.1: Complete extraction.py
**File:** `backend/extraction.py`
**Current State:** Scaffolded with docstrings, missing implementations
**What to Do:**
- [ ] Implement `extract_pdf_with_metadata()` function fully
- [ ] Add PyMuPDF import and error handling
- [ ] Test with sample PDFs (text PDF, large PDF)
- [ ] Verify page numbers are 1-indexed (critical!)
- [ ] Add logging at INFO level

**Acceptance Criteria:**
- Extracts 10-20 page PDF in < 5 seconds
- Returns chunks with page, section, text, metadata
- No stack traces logged
- Handles corrupted PDFs gracefully (returns error, not crash)

**Reference:** See `.claude/skills/pdf-extraction.md`

---

### Task 1.2: Complete evaluation.py
**File:** `backend/evaluation.py`
**Current State:** Scaffolded, LLM calls stubbed
**What to Do:**
- [ ] Implement `evaluate_checklist()` async function
- [ ] Implement `evaluate_single_item()` async function
- [ ] Add Claude API calls with structured output mode
- [ ] Parse JSON responses and validate against Finding schema
- [ ] Add error handling for LLM timeouts (503 status)
- [ ] Add logging for each checklist item
- [ ] Load mock checklist from `load_checklist()` function

**Acceptance Criteria:**
- Evaluates SOC2 checklist (3+ items) against sample PDF
- Returns findings with mandatory supporting_chunks
- Each finding has page numbers (not hallucinated)
- Handles LLM API errors gracefully
- Completes evaluation in < 120 seconds
- No API key logged or exposed

**Reference:** See `.claude/skills/claude-structured-output.md` and `rules/citations-mandatory.md`

---

### Task 1.3: Test Backend Locally
**What to Do:**
- [ ] Create sample PDF file (or use test PDF from task data)
- [ ] Run FastAPI server locally: `uvicorn backend.main:app --reload`
- [ ] Test `/health` endpoint (should return 200)
- [ ] Test `/upload` with sample PDF
- [ ] Test `/evaluate` with document_id from upload
- [ ] Verify `/results/{evaluation_id}` returns findings
- [ ] Check logs for errors, no stack traces exposed

**Acceptance Criteria:**
- All endpoints return expected HTTP status codes
- PDF extraction works without timeout
- Findings include page citations
- No sensitive data in logs

---

## PHASE 2: Frontend Implementation (2-3 hours)

### Task 2.1: Build React Components
**Files:** `frontend/components/` (create these)
**What to Do:**
- [ ] Create `UploadZone.tsx` — drag-drop PDF upload UI
- [ ] Create `ChecklistSelector.tsx` — radio button checklist picker
- [ ] Create `ResultsDisplay.tsx` — show findings with filter options
- [ ] Create `ProgressBar.tsx` — show evaluation progress
- [ ] Create `ErrorAlert.tsx` — display error messages
- [ ] Create `FindingCard.tsx` — single finding with citations + excerpt

**For Each Component:**
- Use Tailwind CSS (already in Next.js)
- Include prop types in TypeScript
- Add error boundaries if needed
- Style for dark theme (slate-900 background)

**Acceptance Criteria:**
- Upload UI accepts PDF drag-and-drop
- Checklist selector shows at least 3 options (SOC2, ESG, Code Review)
- Results page displays findings with filtering by severity
- Citations clickable/expandable to show excerpts
- No console errors, responsive on mobile

**Reference:** Frontend components should use types from `lib/types.ts`

---

### Task 2.2: Connect API Routes
**Files:** 
- `frontend/app/api/upload/route.ts` (separate from `app/api/route.ts`)
- `frontend/app/api/evaluate/route.ts`
- `frontend/app/api/results/[id]/route.ts`
**What to Do:**
- [ ] Split `app/api/route.ts` into three separate route files
- [ ] Each route proxies to FastAPI backend (use `NEXT_PUBLIC_API_URL` env var)
- [ ] Add request validation
- [ ] Add error handling (400, 404, 503, etc.)
- [ ] Return proper HTTP status codes and error format

**Acceptance Criteria:**
- Upload endpoint works with multipart form-data
- Evaluate endpoint starts evaluation asynchronously
- Results endpoint returns findings (or 404 if not ready)
- All errors return JSON with {error, status_code}
- No stack traces exposed

---

### Task 2.3: Test Frontend Locally
**What to Do:**
- [ ] Install dependencies: `npm install` in frontend/
- [ ] Create `.env.local`: `NEXT_PUBLIC_API_URL=http://localhost:8000`
- [ ] Run dev server: `npm run dev`
- [ ] Test upload flow: select PDF → see success message
- [ ] Test checklist selection → see evaluation start
- [ ] Test results display → see findings with citations
- [ ] Test error handling → try oversized PDF, see error

**Acceptance Criteria:**
- Frontend loads without build errors
- End-to-end flow works (upload → checklist → results)
- No console errors or TypeScript warnings
- Error messages display to user
- Mobile responsive

---

## PHASE 3: Integration & Deployment (1-2 hours)

### Task 3.1: Deploy Backend to Render
**What to Do:**
- [ ] Create Render account + link GitHub
- [ ] Create new Web Service in Render
- [ ] Connect to GitHub repo
- [ ] Set environment variables in Render dashboard:
  - `OPENAI_API_KEY` (your Anthropic API key)
  - `BACKEND_URL` (self-reference for CORS)
  - Any others from `.env.template`
- [ ] Set build command: `pip install -r backend/requirements.txt`
- [ ] Set start command: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`
- [ ] Deploy and test `/health` endpoint

**Acceptance Criteria:**
- Render build succeeds (no errors in build log)
- Service is live at `https://auditdoc-backend.onrender.com`
- `/health` endpoint returns 200
- No startup errors in logs

---

### Task 3.2: Deploy Frontend to Vercel
**What to Do:**
- [ ] Create Vercel account + link GitHub
- [ ] Create new project from GitHub repo
- [ ] Set environment variable:
  - `NEXT_PUBLIC_API_URL=https://auditdoc-backend.onrender.com` (from Task 3.1)
- [ ] Deploy (Vercel auto-builds Next.js projects)
- [ ] Test frontend loads and is accessible

**Acceptance Criteria:**
- Vercel build succeeds
- Frontend is live at `https://auditdoc.vercel.app`
- Frontend loads in < 3 seconds
- API calls go to Render backend

---

### Task 3.3: End-to-End Test
**What to Do:**
- [ ] Use production URLs (Vercel + Render)
- [ ] Upload sample PDF via frontend
- [ ] Select checklist and evaluate
- [ ] Verify findings display with citations
- [ ] Test error flow (try invalid file, oversized file)
- [ ] Check browser console — no errors
- [ ] Check Render logs — no 500 errors

**Acceptance Criteria:**
- Complete flow works end-to-end
- Findings display with correct page citations
- No errors exposed to user
- Backend logs show operations (but no sensitive data)
- Performance acceptable (< 120 sec for evaluation)

---

## OPTIONAL: Post-Launch Polish (not MVP)

- [ ] Add sample PDFs + pre-computed results for demo mode
- [ ] Create demo video (Loom, 90 seconds)
- [ ] Add loading spinner animations
- [ ] Add testimonial section
- [ ] Set up Sentry error tracking
- [ ] Add analytics (segment/plausible)
- [ ] Custom domain (auditdoc.app)

---

## Success Criteria (MVP)

✅ **Functionality:**
- Upload PDF → Extract with metadata
- Select checklist → Evaluate with Claude
- Display findings with page citations
- Error handling without exposing internals

✅ **Performance:**
- Upload: < 2 seconds
- Evaluation: < 120 seconds
- Results display: < 500ms
- Frontend load: < 3 seconds

✅ **Quality:**
- All TypeScript warnings resolved
- No console errors
- Findings validated against schema
- Citations are mandatory (no FAIL without page refs)

✅ **Deployment:**
- Backend live on Render
- Frontend live on Vercel
- Both services connected and working

---

## What Claude Code Should NOT Do

❌ Refactor existing scaffolds (they're good)
❌ Add features not listed here (keep MVP focused)
❌ Change error handling patterns (follow rules/)
❌ Log sensitive data or full content
❌ Use localStorage (use React state instead)
❌ Make API calls from client directly (use Next.js API routes)

---

## Reference Files

- `.claude/CLAUDE.md` — Project bible
- `.claude/agents/` — Task descriptions
- `.claude/skills/` — Code patterns to follow
- `.claude/rules/` — Constraints to enforce
- `SHERYLABS_MASTER_CONFIG.md` — Context on business

---

**Ready to build?**

Claude Code: Start with Task 1.1 (extraction.py). Reference the skills/ and rules/ files as you go. Update memory/MEMORY.md as you complete each task.
