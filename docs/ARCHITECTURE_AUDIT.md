# Architecture Audit — Interview-ai-er

> **Audit Date:** 2026-09-30  
> **Auditor:** Engineering takeover review  
> **Commit Base:** Current HEAD (pre-fork)

---

## 1. Repository Layout

```
Interview-ai-er/
├── app.py                          # Flask entry point
├── config.py                       # Multi-environment config (unused at runtime)
├── requirements.txt                # 5 Python deps (unpinned)
├── database_schema.sql             # Original schema
├── database_migration.sql          # Migration v1
├── migrate_database.sql            # Migration v2 (duplicates v1)
├── deploy.py                       # Deployment script
├── debug_db.py                     # Debug utility
├── test_*.py (×7)                  # Test files (none use pytest fixtures)
├── app/
│   ├── __init__.py                 # Flask app factory
│   ├── models/
│   │   └── __init__.py             # Empty (no ORM models)
│   ├── routes/
│   │   ├── interview.py            # 12 endpoints (712 lines)
│   │   └── logging.py              # 6 endpoints (305 lines)
│   └── services/
│       ├── gemini_service.py       # AI service (501 lines)
│       ├── supabase_service.py     # DB service (377 lines)
│       └── security_service.py     # Cheating detection (50 lines)
├── frontend/                       # Next.js 15 + TailwindCSS 4
│   ├── app/
│   │   ├── page.tsx                # Landing page
│   │   ├── login/page.tsx          # Auth login
│   │   ├── signup/page.tsx         # Auth signup
│   │   ├── dashboard/page.tsx      # Dashboard (MOCKED data)
│   │   ├── interview/page.tsx      # Interview session
│   │   ├── ide/page.tsx            # Standalone IDE
│   │   ├── chat/page.tsx           # AI Chat
│   │   ├── practice/page.tsx       # Practice mode
│   │   ├── analytics/page.tsx      # Charts (HARDCODED data)
│   │   ├── history/page.tsx        # Stub ("No history yet")
│   │   └── api/
│   │       ├── ai/ask/route.ts     # Gemini non-streaming
│   │       ├── ai/stream/route.ts  # Gemini streaming
│   │       └── execute/route.ts    # FAKE code execution
│   ├── components/
│   │   ├── interview/              # 5 interview components
│   │   ├── ide/                    # 2 editor components
│   │   ├── anti-cheat/             # 1 guard component
│   │   ├── chat/                   # 2 chat components
│   │   ├── realtime/               # 1 presence provider
│   │   └── ui/                     # 50 shadcn/ui components
│   ├── lib/
│   │   ├── api-client.ts           # Flask backend HTTP client
│   │   ├── supabase.ts             # Supabase browser/server clients
│   │   └── utils.ts                # cn() utility
│   └── middleware.ts               # Auth guard (bypassed without env vars)
└── memory-bank/                    # Cursor IDE context files
```

---

## 2. Actual Data Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                               │
│  Next.js 15  ──── api-client.ts ──→ Flask :5000/api/*              │
│              ──── /api/ai/ask   ──→ Gemini (via Vercel AI SDK)     │
│              ──── /api/ai/stream──→ Gemini streaming               │
│              ──── /api/execute  ──→ FAKE (returns string)          │
│              ──── supabase.ts   ──→ Supabase Auth (client-direct)  │
└──────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                          FLASK BACKEND                              │
│  Routes → Services → Supabase REST API (anon key)                  │
│                    → Gemini 1.5 Pro (google-generativeai SDK)       │
│  NO authentication middleware. NO JWT validation.                   │
│  Accepts any user_id string from the request body.                  │
└──────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     SUPABASE / POSTGRES                             │
│  Tables: sessions, questions, logs, anomalies                      │
│  Migration tables: security_events, code_submissions,              │
│                    practice_sessions (may not exist)                │
│  RLS: Enabled but bypassed — backend uses anon key with            │
│       user_id from untrusted request body                          │
└──────────────────────────────────────────────────────────────────────┘
```

### Critical Data Flow Issues

1. **Dual AI pathways**: Frontend calls Gemini directly via `/api/ai/*` AND calls Flask which calls Gemini via `gemini_service.py`. Two separate API keys, two models (`gemini-1.5-flash` vs `gemini-1.5-pro`), no shared context.
2. **No auth on Flask**: The backend accepts any `user_id` string. No JWT, no session token, no API key.
3. **Frontend generates session IDs**: `interview/page.tsx` generates `session_${Date.now()}` — a non-UUID string that will fail Supabase UUID column validation.
4. **RLS bypassed**: Backend uses the Supabase anon key but inserts arbitrary `user_id` values (not `auth.uid()`), meaning RLS policies checking `auth.uid()` will reject or allow wrong data.

---

## 3. Backend Route Inventory

| Route | Method | Status | Service Call | DB Operation | Notes |
|-------|--------|--------|-------------|--------------|-------|
| `/api/start_session` | POST | **PARTIAL** | `supabase_service.create_session()` | INSERT sessions | Accepts untrusted user_id |
| `/api/get_question` | GET | **PARTIAL** | `gemini_service.generate_question()` → `supabase_service.store_question()` | INSERT questions | Stores Gemini dict as `question_text` (type mismatch) |
| `/api/submit_answer` | POST | **PARTIAL** | `gemini_service.evaluate_answer()` → `supabase_service.store_answer()` | UPDATE questions | Score averaging is naive: `(current + new) / 2` |
| `/api/submit_code` | POST | **PARTIAL** | `gemini_service.evaluate_code()` → `supabase_service.store_code_submission()` | UPDATE questions | Argument order mismatch in evaluate_code call |
| `/api/session/<id>` | GET | **IMPLEMENTED** | `supabase_service.get_session_statistics()` | SELECT from 4 tables | Works if session exists |
| `/api/end_session/<id>` | POST | **IMPLEMENTED** | `supabase_service.end_session()` | UPDATE sessions | Duration not calculated |
| `/api/user/<id>/sessions` | GET | **IMPLEMENTED** | `supabase_service.get_user_sessions()` | SELECT sessions | No auth check |
| `/api/follow_up_question` | POST | **PARTIAL** | `gemini_service.generate_follow_up_question()` | None | Passes `interview_type` string where `evaluation` dict expected |
| `/api/security/check` | POST | **PARTIAL** | `security_service.detect_cheating()` | INSERT anomalies | References `confidence` key that doesn't exist in return value |
| `/api/security/report/<id>` | GET | **MOCKED** | `security_service.get_security_report()` | None | Method does NOT exist on SecurityService — will 500 |
| `/api/practice/coding` | POST | **PARTIAL** | `gemini_service.generate_coding_question()` | None | Argument mismatch: calls `(type, difficulty, topic)` but signature is `(topic, difficulty)` |
| `/api/log_event` | POST | **IMPLEMENTED** | `supabase_service.log_event()` | INSERT logs | Works |
| `/api/log_anomaly` | POST | **IMPLEMENTED** | `supabase_service.log_anomaly()` | INSERT anomalies | Works |
| `/api/events/<id>` | GET | **PLACEHOLDER** | None | None | Returns empty `[]` |
| `/api/anomalies/<id>` | GET | **PLACEHOLDER** | None | None | Returns empty `[]` |
| `/api/health` | GET | **IMPLEMENTED** | `supabase_service.health_check()` | SELECT count | Works |
| `/api/metrics` | GET | **MOCKED** | None | None | Returns hardcoded zeros |

---

## 4. Frontend Screen Inventory

| Screen | Route | Data Source | Status |
|--------|-------|-------------|--------|
| Landing | `/` | Static | **IMPLEMENTED** |
| Login | `/login` | Supabase Auth (client-side) | **PARTIAL** — no error UX, crashes if Supabase not configured |
| Signup | `/signup` | Supabase Auth (client-side) | **PARTIAL** — same issues as login |
| Dashboard | `/dashboard` | **HARDCODED mock data** | **MOCKED** — uses inline mock arrays, never calls API |
| Interview | `/interview` | Flask API via `apiClient` | **PARTIAL** — generates fake session IDs |
| IDE | `/ide` | Monaco editor + simulated execution | **PARTIAL** — editor works, execution is fake |
| Chat | `/chat` | Next.js `/api/ai/stream` → Gemini | **PARTIAL** — real Gemini streaming, no persistence |
| Practice | `/practice` | **HARDCODED mock questions** | **MOCKED** |
| Analytics | `/analytics` | **HARDCODED static arrays** | **MOCKED** |
| History | `/history` | None | **PLACEHOLDER** |

---

## 5. AI Model Usage

### Backend (Flask)
- **Model**: `gemini-1.5-pro` via `google-generativeai` SDK
- **Parsing**: String-based JSON extraction — searches for ` ```json ` markers, then `json.loads()`. No schema validation, no retry.
- **Fallback**: Every method returns hardcoded scores of 70 with `model_used: "fallback"` on any exception. This masks failures silently.
- **Status**: **PARTIAL**

### Frontend (Next.js API Routes)
- **Model**: `gemini-1.5-flash` via `@ai-sdk/google` (Vercel AI SDK)
- **API Key**: `GOOGLE_GENERATIVE_AI_API_KEY` (different env var from backend's `GEMINI_API_KEY`)
- **Status**: **IMPLEMENTED** for chat only

### Key Issues
1. Two different Gemini models across separate API pathways with no shared context
2. No structured output — relies on LLM to produce valid JSON, no JSON mode or function calling
3. Fallback data indistinguishable from real evaluations
4. No token counting, rate limiting, or cost tracking
5. Prompt injection vulnerability — user answers interpolated directly into prompts

---

## 6. Database Schema Analysis

### Core Tables

| Table | RLS | Issues |
|-------|-----|--------|
| `sessions` | ✅ | user_id references `auth.users(id)` but backend inserts arbitrary strings |
| `questions` | ✅ | Missing columns needed by backend unless migration applied |
| `logs` | ✅ | Functional |
| `anomalies` | ✅ | Functional |

### Migration Issues
- **Two nearly identical migration files**: `database_migration.sql` and `migrate_database.sql`
- Migration adds `security_events`, `code_submissions`, `practice_sessions` — **no backend code uses these tables**
- No migration tooling — raw SQL with no versioning or idempotency tracking

### RLS Policy Issues
- All policies use `auth.uid()` — but Flask backend uses anon key, not user JWT
- This means RLS either blocks all backend ops or has been disabled

---

## 7. Authentication & Authorization

| Layer | Mechanism | Status |
|-------|-----------|--------|
| Frontend middleware | Supabase SSR `getUser()` → redirect | **PARTIAL** — bypassed when env vars missing |
| Frontend login/signup | Supabase Auth | **PARTIAL** — minimal, no password reset |
| Flask backend | **NONE** | **UNVERIFIED** — no JWT, no API key, no session tokens |
| Supabase RLS | `auth.uid()` policies | **PARTIAL** — likely bypassed |

### Critical: Any client can impersonate any user by sending arbitrary `user_id`.

---

## 8. Code Execution

| Component | What It Does | Status |
|-----------|-------------|--------|
| `/api/execute` (Next.js) | Returns static string | **MOCKED** |
| `enhanced-code-editor.tsx` `runCode()` | `setTimeout` + hardcoded `"Result: 9"` | **MOCKED** |
| `submit_code` (Flask) | Sends code to Gemini for AI analysis only | **PARTIAL** |

**Zero real code execution anywhere in the system.**

---

## 9. Anti-Cheating / Proctoring

| Feature | Status | Detail |
|---------|--------|--------|
| Tab switch detection | **IMPLEMENTED** | `window.blur` + `visibilitychange` |
| DevTools detection | **PARTIAL** | Width heuristic, unreliable |
| Typing cadence | **PARTIAL** | Simplistic 40ms threshold |
| Paste detection | **IMPLEMENTED** | >50 chars triggers flag |
| Webcam monitoring | **PARTIAL** | Acquires stream but **no face detection** |
| Audio analysis | **PLACEHOLDER** | Claimed on landing page, no code |
| Face detection | **PLACEHOLDER** | No implementation |
| Gaze tracking | **PLACEHOLDER** | No implementation |
| Enforcement | **PLACEHOLDER** | Flags displayed but never block interview |

---

## 10. Dead Code & Duplication

| Item | Type |
|------|------|
| `config.py` | Dead — never imported by app factory |
| `deploy.py` | Dead — unclear if functional |
| `debug_db.py` | Dead |
| `app/models/__init__.py` | Stub — empty |
| `test_*.py` (×7) | Stale — patterns don't match current code |
| `database_migration.sql` + `migrate_database.sql` | Duplicate migrations |
| `interview-session.tsx` | Unused — not imported anywhere |
| `timer.tsx` | Duplicate of `interview-timer.tsx` |
| `README.md` + `README_ENHANCED.md` | Duplicate/aspirational docs |
| `pnpm-lock.yaml` | Invalid — 96 bytes |
| `@remix-run/react`, `svelte`, `vue`, `vue-router` | Stale deps — wrong frameworks |

---

## 11. Production Deployment Weaknesses

1. No Dockerfile or container setup
2. Flask runs with `debug=True` and `host='0.0.0.0'`
3. No WSGI server (uses dev server)
4. Unpinned dependencies
5. Broken lockfile
6. No CI/CD pipeline
7. No monitoring or alerting
8. Logs written to local `app.log`
