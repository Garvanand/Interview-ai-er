# Current System Map — Interview-ai-er

> **Generated:** 2026-09-30  
> **Purpose:** Capability-level truth table of every feature in the system

---

## Capability Classification Legend

| Tag | Meaning |
|-----|---------|
| **IMPLEMENTED** | Feature works end-to-end with real data |
| **PARTIAL** | Some real code exists but has bugs, missing integrations, or incomplete flows |
| **MOCKED** | UI exists but data is hardcoded, simulated, or fabricated |
| **PLACEHOLDER** | Route/component exists but returns empty data or stub text |
| **UNVERIFIED** | Code exists but cannot be confirmed working without live services |

---

## Master Capability Map

### Authentication & User Management

| Capability | Frontend | Backend | Database | Classification |
|-----------|----------|---------|----------|----------------|
| Email/password signup | `signup/page.tsx` calls Supabase Auth | None (client-direct) | Supabase `auth.users` | **PARTIAL** — no validation, no error handling |
| Email/password login | `login/page.tsx` calls Supabase Auth | None (client-direct) | Supabase `auth.users` | **PARTIAL** — crashes if Supabase not configured |
| Protected route middleware | `middleware.ts` checks `getUser()` | N/A | N/A | **PARTIAL** — bypassed entirely when env vars missing |
| Password reset | None | None | N/A | **PLACEHOLDER** — no UI or logic |
| OAuth providers | None | None | N/A | **PLACEHOLDER** — not implemented |
| User profile | None | None | No `profiles` table | **PLACEHOLDER** |
| Backend auth validation | None | None | N/A | **UNVERIFIED** — Flask accepts any user_id |
| Session token management | Cookie-based via Supabase SSR | Not validated by Flask | N/A | **PARTIAL** |

### Interview Sessions

| Capability | Frontend | Backend | Database | Classification |
|-----------|----------|---------|----------|----------------|
| Create session | `interview/page.tsx` generates `session_${Date.now()}` | `POST /api/start_session` → INSERT | `sessions` table | **PARTIAL** — frontend generates fake IDs, doesn't call backend |
| Session state (active/completed) | Client-side state only | UPDATE on end_session | `sessions.status` | **PARTIAL** |
| Session timer | `interview-timer.tsx` countdown | None | None | **IMPLEMENTED** (client-only) |
| Session resume | None | None | None | **PLACEHOLDER** |
| Session history list | Static "No history yet" text | `GET /api/user/<id>/sessions` | `sessions` table | **PLACEHOLDER** (frontend) / **IMPLEMENTED** (backend) |
| Multi-session management | None | None | None | **PLACEHOLDER** |

### Question Generation

| Capability | Frontend | Backend | Database | Classification |
|-----------|----------|---------|----------|----------------|
| AI question generation | Displays question text | `gemini_service.generate_question()` → Gemini 1.5 Pro | `questions` table | **PARTIAL** — works but stores entire dict as question_text |
| Difficulty levels | UI badges (Easy/Medium/Hard) | URL param passed to Gemini prompt | None | **PARTIAL** — no adaptive adjustment |
| Question types | Badge display | Included in Gemini prompt | `questions.interview_type` | **PARTIAL** |
| Follow-up questions | None in main flow | `POST /api/follow_up_question` | Not stored | **PARTIAL** — argument type mismatch causes error |
| Question de-duplication | None | None | None | **PLACEHOLDER** |
| Question bank | None | None | None | **PLACEHOLDER** |
| Coding question generation | Via practice page | `gemini_service.generate_coding_question()` | Not stored | **PARTIAL** — argument mismatch |

### Answer Evaluation

| Capability | Frontend | Backend | Database | Classification |
|-----------|----------|---------|----------|----------------|
| Text answer evaluation | Textarea → submit → display score | `gemini_service.evaluate_answer()` → Gemini | `questions.evaluation_*` | **PARTIAL** — real AI eval but no rubric |
| Multi-dimensional scoring | Displayed if returned | Requested in Gemini prompt | Stored as JSONB | **UNVERIFIED** — scores are unvalidated LLM output |
| Feedback display | Shows evaluation object | Part of Gemini response | Stored | **PARTIAL** |
| Score aggregation | Displayed in session | `(current + new) / 2` | `sessions.score` | **PARTIAL** — mathematically wrong for running average |

### Code Editor & Execution

| Capability | Frontend | Backend | Database | Classification |
|-----------|----------|---------|----------|----------------|
| Monaco editor | `enhanced-code-editor.tsx` | N/A | N/A | **IMPLEMENTED** |
| Multi-language support | 8 language options with snippets | N/A | N/A | **IMPLEMENTED** (editor only) |
| Code execution | `setTimeout` + hardcoded "Result: 9" | `/api/execute` returns static string | None | **MOCKED** |
| Code evaluation (AI) | Submit button → display results | `gemini_service.evaluate_code()` → Gemini | `questions.code_*` | **PARTIAL** — AI analysis, no real execution |
| Test case execution | None | None | None | **PLACEHOLDER** |
| Syntax highlighting | Monaco built-in | N/A | N/A | **IMPLEMENTED** |

### AI Chat

| Capability | Frontend | Backend | Database | Classification |
|-----------|----------|---------|----------|----------------|
| AI chat conversation | `chat/page.tsx` + `interview-chat.tsx` | `/api/ai/stream` → Gemini 1.5 Flash | None (not persisted) | **PARTIAL** — works but no session context |
| Streaming responses | Vercel AI SDK `streamText` | Next.js API route | None | **IMPLEMENTED** |
| Interview-context chat | `interview-chat.tsx` with hints/clarification | `/api/ai/ask` | None | **PARTIAL** — no real context injection |
| Voice input (STT) | `voice-controls.tsx` Web Speech API | None | None | **PARTIAL** — browser-dependent, Chrome-only |
| Voice output (TTS) | `SpeechSynthesisUtterance` | None | None | **PARTIAL** — browser built-in |
| Chat history persistence | None | None | None | **PLACEHOLDER** |

### Anti-Cheating / Proctoring

| Capability | Frontend | Backend | Database | Classification |
|-----------|----------|---------|----------|----------------|
| Tab switch detection | `window.blur` + `visibilitychange` | None | None | **IMPLEMENTED** (client-side flag) |
| DevTools detection | Width/height diff heuristic | None | None | **PARTIAL** — unreliable |
| Typing cadence analysis | Keystroke delta analysis | None | None | **PARTIAL** — simplistic |
| Paste detection | `clipboardData` length check | None | None | **IMPLEMENTED** |
| Webcam stream capture | `getUserMedia({video: true})` | None | None | **PARTIAL** — stream acquired, no analysis |
| Face detection | None | `face_count` param accepted | None | **PLACEHOLDER** |
| Gaze tracking | None | None | None | **PLACEHOLDER** |
| Audio analysis | None | None | None | **PLACEHOLDER** |
| Risk score calculation | None | `SecurityService.detect_cheating()` | `anomalies` table | **PARTIAL** — 3 hardcoded heuristics |
| Cheating enforcement | Flags displayed, never blocks | None | None | **PLACEHOLDER** |
| Security report | None | `get_security_report()` → **DOES NOT EXIST** | None | **MOCKED** (will 500) |

### Analytics & Reporting

| Capability | Frontend | Backend | Database | Classification |
|-----------|----------|---------|----------|----------------|
| Score trend chart | Recharts with hardcoded data | None | None | **MOCKED** |
| Category performance chart | Recharts with hardcoded data | None | None | **MOCKED** |
| Dashboard metrics | Hardcoded mock sessions | `/api/metrics` returns zeros | None | **MOCKED** |
| Skill breakdown | Hardcoded percentages | None | None | **MOCKED** |
| Session statistics | None | `supabase_service.get_session_statistics()` | Real queries | **IMPLEMENTED** (backend only) |
| Export report | Button exists, no handler | None | None | **PLACEHOLDER** |
| Improvement suggestions | Hardcoded bullet points | None | None | **MOCKED** |

### Event Logging

| Capability | Frontend | Backend | Database | Classification |
|-----------|----------|---------|----------|----------------|
| Event logging | `apiClient.logEvent()` | `POST /api/log_event` → INSERT | `logs` table | **IMPLEMENTED** |
| Anomaly logging | `apiClient.logAnomaly()` | `POST /api/log_anomaly` → INSERT | `anomalies` table | **IMPLEMENTED** |
| Event retrieval | None | `GET /api/events/<id>` → empty array | None | **PLACEHOLDER** |
| Anomaly retrieval | None | `GET /api/anomalies/<id>` → empty array | None | **PLACEHOLDER** |

### Realtime Features

| Capability | Frontend | Backend | Database | Classification |
|-----------|----------|---------|----------|----------------|
| Socket.IO presence | `realtime-provider.tsx` | No Socket.IO server | None | **PARTIAL** — client code exists, no server |
| BroadcastChannel fallback | Same-browser tab presence | N/A | N/A | **IMPLEMENTED** (local tabs only) |
| Live collaboration | None | None | None | **PLACEHOLDER** |

### Practice Mode

| Capability | Frontend | Backend | Database | Classification |
|-----------|----------|---------|----------|----------------|
| Practice question display | Hardcoded mock questions | `POST /api/practice/coding` | `practice_sessions` (migration-only) | **MOCKED** |
| Practice scoring | Frontend-only mock scores | None | None | **MOCKED** |
| Practice progress tracking | None | None | None | **PLACEHOLDER** |

---

## Data Persistence Summary

| Data Type | Actually Persisted? | Where | Notes |
|-----------|-------------------|-------|-------|
| User accounts | Yes | Supabase Auth | Via client-side Supabase SDK |
| Interview sessions | Maybe | `sessions` table | Depends on RLS config and whether frontend actually calls backend |
| Questions | Maybe | `questions` table | Same dependency |
| Answers + evaluations | Maybe | `questions` table (update) | Same dependency |
| Code submissions | Maybe | `questions` table (update) | Separate `code_submissions` table unused |
| Event logs | Maybe | `logs` table | Same dependency |
| Anomaly logs | Maybe | `anomalies` table | Same dependency |
| Chat history | No | — | Not persisted anywhere |
| Analytics data | No | — | All hardcoded in frontend |
| Practice progress | No | — | `practice_sessions` table exists in migration but unused |
| Security events | No | — | `security_events` table exists in migration but unused |
| Webcam/audio recordings | No | — | Stream acquired but never saved |
| User preferences | No | — | No preferences system |

---

## API Endpoint Summary

### Flask Backend (18 routes)

| Status | Count | Routes |
|--------|-------|--------|
| **IMPLEMENTED** | 6 | `log_event`, `log_anomaly`, `session/<id>`, `end_session/<id>`, `user/<id>/sessions`, `health` |
| **PARTIAL** | 6 | `start_session`, `get_question`, `submit_answer`, `submit_code`, `follow_up_question`, `security/check` |
| **MOCKED** | 2 | `security/report/<id>`, `metrics` |
| **PLACEHOLDER** | 2 | `events/<id>`, `anomalies/<id>` |
| **With Bugs** | 4 | `submit_code` (arg mismatch), `practice/coding` (arg mismatch), `security/check` (missing key), `security/report` (missing method) |

### Next.js API Routes (3 routes)

| Status | Count | Routes |
|--------|-------|--------|
| **IMPLEMENTED** | 2 | `/api/ai/ask`, `/api/ai/stream` |
| **MOCKED** | 1 | `/api/execute` |
