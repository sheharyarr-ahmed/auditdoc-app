# CLAUDE.md — AuditDoc Project Bible

## 🎯 PROJECT MISSION

Build **AuditDoc**: A compliance document intelligence system that transforms PDF documents into structured, auditable findings using AI with mandatory citations.

**Core Value:** 45-second compliance evaluation (vs 4-8 hours manual) with zero hallucinated citations.

---

## 📋 PROJECT STRUCTURE

```
auditdoc/
├── backend/              # FastAPI application
│   ├── main.py          # Entry point, API routes
│   ├── extraction.py    # PDF → chunks with metadata
│   ├── evaluation.py    # Chunks → LLM evaluation → findings
│   ├── schemas.py       # Pydantic models
│   └── requirements.txt # Dependencies
├── frontend/            # Next.js application
│   ├── app/
│   │   ├── page.tsx     # Main UI (upload, results)
│   │   └── api/         # API proxy routes
│   ├── lib/
│   │   └── types.ts     # TypeScript interfaces
│   ├── components/      # React components (TODO)
│   └── package.json
├── .claude/            # Claude Code configuration
│   ├── CLAUDE.md       # This file
│   ├── agents/         # Task agents
│   ├── skills/         # Reusable patterns
│   ├── rules/          # Constraints & guardrails
│   └── memory/         # Session memory
└── .env.template       # Environment variables
```

---

## 🔧 CORE TECH STACK

### Backend
- **Framework:** FastAPI 0.109.0 (async Python)
- **PDF Processing:** PyMuPDF (fitz) for extraction with metadata
- **LLM:** Anthropic Claude 4.x (Sonnet 4.6 default, Opus 4.7 for hard items) with tool-use structured output. Key read from `ANTHROPIC_API_KEY`.
- **Validation:** Pydantic v2 (mandatory schema enforcement)
- **Deployment:** Render.com (single container, auto-scaling)

### Frontend
- **Framework:** Next.js 14 with App Router
- **Language:** TypeScript (strict mode required)
- **UI:** Tailwind CSS + Headless components
- **Deployment:** Vercel (automatic from git push)

### Database (Future Phase)
- **Primary:** Supabase (PostgreSQL + pgvector for embeddings)
- **Auth:** Supabase Auth with Row-Level Security

---

## ⚡ CRITICAL CONSTRAINTS

### 1. CITATIONS ARE MANDATORY
- Every Finding MUST have supporting_chunks
- supporting_chunks MUST include: page number, section, excerpt
- If LLM cannot cite, status must be PARTIAL or NOT_APPLICABLE
- **Rationale:** Eliminate hallucinations — enable human verification

### 2. ERROR HANDLING IS EXPLICIT
- Every API call wrapped in try/catch
- HTTP status codes must be specific (400, 404, 429, 503)
- Error responses include: error message, status_code, timestamp
- **Never expose** stack traces to frontend

### 3. TYPE SAFETY IS ENFORCED
- Python: All functions have type hints (-> ReturnType)
- TypeScript: Use strict mode, no `any` types
- Pydantic: All schemas validate before processing
- **Rationale:** Catch bugs at dev time, not production

### 4. PDF PROCESSING IS SAFE
- Max file size: 50MB (reject > 50MB with 400)
- Max pages: 500 (warn user if > 500)
- Timeout: 60 seconds max for extraction + evaluation
- **Rationale:** Prevent DOS, manage costs

### 5. LLM EVALUATIONS MUST TIMEOUT
- Single item evaluation: max 30 seconds
- Full checklist: max 120 seconds per evaluation
- Backend tracks timing, alerts if > 80% of limit
- **Rationale:** Predictable user experience, cost control

---

## 📝 API CONTRACTS

### POST /upload
**Request:** Multipart form with file
**Response:**
```json
{
  "document_id": "uuid-1234",
  "filename": "report.pdf",
  "size": 2048576,
  "status": "uploaded"
}
```
**Errors:** 400 (invalid PDF), 413 (too large), 500 (server error)

### POST /evaluate
**Request:**
```json
{
  "document_id": "uuid-1234",
  "checklist_id": "soc2_trust_services"
}
```
**Response:**
```json
{
  "evaluation_id": "uuid-5678",
  "document_id": "uuid-1234",
  "checklist_id": "soc2_trust_services",
  "status": "completed",
  "findings": [...],
  "summary": "4 CRITICAL, 8 HIGH, 3 MEDIUM"
}
```
**Errors:** 400 (invalid request), 404 (document not found), 503 (timeout)

### GET /results/{evaluation_id}
**Response:** Full EvaluationResult with all findings + citations

---

## 🎯 SUCCESS CRITERIA

### For MVP Launch
- [x] Extract PDF → chunks with page/section metadata
- [x] Evaluate checklist items via Claude with structured output
- [x] Return findings with mandatory citations
- [x] Handle errors without exposing stack traces
- [x] Deploy frontend to Vercel, backend to Render

### For Beta (Post-Launch)
- [ ] Multi-user authentication (Supabase Auth)
- [ ] Custom checklist upload
- [ ] Evaluation history + comparison
- [ ] Accuracy metrics (ground truth testing)
- [ ] Advanced search (pgvector semantic search)

---

## 💡 DEVELOPMENT WORKFLOW

### When Building Components
1. Write TypeScript interfaces first (frontend) or Pydantic models (backend)
2. Implement with full error handling
3. Add logging at INFO level for important steps
4. Test with sample data before commit

### When Adding Features
1. Update CLAUDE.md first (document your decision)
2. Add to appropriate skill/rule file
3. Run through checklist of constraints (#Critical Constraints section)
4. Commit with conventional commit message

### When Debugging
1. Check logs first (search by error message)
2. Reproduce with minimal test case
3. Add logging before fixing (to catch future regressions)
4. Commit fix with issue number in message

---

## 🔐 SECURITY RULES

### API Keys
- NEVER commit `.env` files with real keys
- Store only in environment variables
- Rotate keys monthly in production

### PDF Processing
- Validate file magic bytes (not just extension)
- Scan extracted text for secrets/PII (future phase)
- Delete PDFs from temp storage after 24 hours

### LLM Calls
- Never log full document content
- Log: operation (extraction/eval), duration, token count, status only
- Rate-limit per user (20 uploads/hour, 60 evaluations/hour)

---

## 📊 LOGGING STANDARDS

```python
# Good
logger.info(f"Extracting PDF {document_id}: starting")
logger.error(f"PDF extraction failed for {document_id}: {error_type}")

# Bad
logger.info("Starting extraction")  # Too vague
logger.error(f"Error: {full_document_content}")  # Logs sensitive data
```

---

## 🚀 DEPLOYMENT CHECKLIST

Before shipping to production:

- [ ] All environment variables set in Render/Vercel dashboards
- [ ] Database migrations run (if using Supabase)
- [ ] Rate limiting enabled on backend
- [ ] Error tracking enabled (Sentry, etc.)
- [ ] HTTPS enforced on all endpoints
- [ ] CORS restricted to frontend domain only
- [ ] Logging set to INFO level (not DEBUG)
- [ ] README updated with deployment instructions

---

## 📚 REFERENCES

- **Anthropic Structured Output:** https://docs.anthropic.com/en/docs/build-with-claude/guides/structured-output
- **PyMuPDF Documentation:** https://pymupdf.readthedocs.io/
- **FastAPI:** https://fastapi.tiangolo.com/
- **Next.js:** https://nextjs.org/docs

---

**Last Updated:** April 25, 2026
**Version:** 1.0.0
**Maintainer:** Sheharyar Ahmed (Shery Labs)
