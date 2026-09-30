# Technical Debt Register — Interview-ai-er

> **Generated:** 2026-09-30  
> **Severity Scale:** 🔴 Critical · 🟠 High · 🟡 Medium · 🟢 Low

---

## Category 1: Security Vulnerabilities

### TD-SEC-01: No Backend Authentication 🔴
**Location:** `app/routes/interview.py`, `app/routes/logging.py`  
**Description:** The Flask backend has zero authentication. Any HTTP client can call any endpoint, impersonate any user by supplying an arbitrary `user_id` in the request body, and access any session data.  
**Impact:** Complete data integrity compromise. Any user can read, write, or delete any other user's interview data.  
**Remediation:** Implement JWT validation middleware that extracts and verifies Supabase auth tokens from request headers.

### TD-SEC-02: Supabase RLS Bypass 🔴
**Location:** `app/services/supabase_service.py`, `database_schema.sql`  
**Description:** RLS policies check `auth.uid()` but the Flask backend uses the Supabase anon key and inserts `user_id` values from untrusted client input. RLS either blocks all operations (broken app) or has been disabled (no data isolation).  
**Impact:** Either the app doesn't work, or there's no row-level security.  
**Remediation:** Use Supabase service_role key for backend operations, or implement proper JWT forwarding to Supabase.

### TD-SEC-03: Prompt Injection Vulnerability 🟠
**Location:** `app/services/gemini_service.py` (all methods)  
**Description:** User-provided text (answers, code) is interpolated directly into prompt strings via f-strings with no sanitization.  
**Impact:** Users could manipulate AI scoring by injecting prompt-altering text in their answers.  
**Remediation:** Use structured prompts with clear delimiters, input sanitization, and Gemini's system instruction features.

### TD-SEC-04: Flask Secret Key Default 🟠
**Location:** `app/__init__.py:15`  
**Description:** `SECRET_KEY` defaults to `'dev-secret-key'` when env var is missing.  
**Impact:** Session cookie forgery in development/misconfigured deployments.  
**Remediation:** Fail startup if SECRET_KEY not set in production.

### TD-SEC-05: Debug Mode in Production 🟠
**Location:** `app.py:84`  
**Description:** `app.run(debug=True)` is hardcoded — enables interactive debugger and reloader.  
**Impact:** Code execution via Werkzeug debugger if exposed publicly.  
**Remediation:** Use environment-based config, never hardcode `debug=True`.

### TD-SEC-06: No Rate Limiting 🟡
**Location:** `config.py` (defined but never implemented)  
**Description:** Rate limit config exists but no rate limiting middleware is installed.  
**Impact:** AI API abuse, denial of service, cost overrun.  
**Remediation:** Install `flask-limiter` and configure per-endpoint limits.

### TD-SEC-07: No CSRF Protection 🟡
**Location:** `app/__init__.py`  
**Description:** No CSRF tokens. Cookie `SameSite=Lax` provides partial protection.  
**Impact:** Cross-site request forgery on state-changing endpoints.  
**Remediation:** Implement CSRF token validation for all POST endpoints.

---

## Category 2: Architectural Issues

### TD-ARCH-01: Dual AI Pathway 🟠
**Location:** Flask `gemini_service.py` (Gemini 1.5 Pro) + Next.js `/api/ai/*` (Gemini 1.5 Flash)  
**Description:** Two completely separate AI integration paths using different models, different SDKs, different API keys, and different env vars. No shared context, no unified prompting strategy.  
**Impact:** Inconsistent AI behavior, split billing, duplicated maintenance.  
**Remediation:** Consolidate all AI calls through a single backend service with unified model selection and prompt management.

### TD-ARCH-02: Frontend-Backend Mismatch 🟠
**Location:** `frontend/app/interview/page.tsx:19`  
**Description:** The interview page generates `session_${Date.now()}` as session ID instead of calling the backend's `POST /api/start_session`. This non-UUID string will fail Supabase UUID column validation.  
**Impact:** The primary interview flow never creates a real backend session.  
**Remediation:** Wire frontend session creation to the backend API.

### TD-ARCH-03: No Data Model Layer 🟡
**Location:** `app/models/__init__.py` (empty)  
**Description:** No ORM models, no data classes, no schema validation. Services construct dicts manually and hope column names match.  
**Impact:** Runtime errors from column mismatches, no type safety, no validation.  
**Remediation:** Define Pydantic models for all data entities.

### TD-ARCH-04: Service Instantiation Pattern 🟡
**Location:** `app/routes/interview.py:14-16`  
**Description:** Services are instantiated at module import time as globals, but `SupabaseService` requires Flask app context for config. Gemini service validates API key at construction time.  
**Impact:** Import failures if env vars missing, singleton state across requests.  
**Remediation:** Use dependency injection or Flask's application context properly.

### TD-ARCH-05: Config System Unused 🟢
**Location:** `config.py`  
**Description:** 145 lines of multi-environment config (Dev/Test/Prod/Staging) that are never loaded by the app factory.  
**Impact:** Dead code, no environment-specific behavior.  
**Remediation:** Either integrate with `create_app()` or remove.

---

## Category 3: Data Integrity Issues

### TD-DATA-01: Score Averaging Algorithm 🟠
**Location:** `app/routes/interview.py:270`  
**Description:** `new_score = (current_score + evaluation.score) / 2`. This doesn't compute a running average — each new score halves the contribution of all previous scores. After 5 questions, the first score has only 1/32 weight.  
**Impact:** Session scores are mathematically wrong and not meaningful.  
**Remediation:** Track question count and compute `sum / count` or use weighted average.

### TD-DATA-02: Question Text Type Mismatch 🟠
**Location:** `app/routes/interview.py:143-146`  
**Description:** `gemini_service.generate_question()` returns a dict (with question, type, difficulty, hints, etc.) but `supabase_service.store_question()` expects a string for `question_text`. The entire dict is likely stringified.  
**Impact:** Question text in database is `{'question': '...', 'type': '...'}` instead of the actual question.  
**Remediation:** Extract the question text from the dict before storage, store metadata separately.

### TD-DATA-03: Duplicate Migration Scripts 🟡
**Location:** `database_migration.sql` (7742 bytes), `migrate_database.sql` (6362 bytes)  
**Description:** Two nearly identical migration scripts adding the same columns. No migration versioning or tracking.  
**Impact:** Confusion about schema state, potential errors running both.  
**Remediation:** Consolidate into single schema file or adopt proper migration tooling.

### TD-DATA-04: Unused Database Tables 🟡
**Location:** `database_migration.sql` — `security_events`, `code_submissions`, `practice_sessions`  
**Description:** Three tables defined in migrations but never read from or written to by any backend code.  
**Impact:** Schema/code divergence, wasted resources.  
**Remediation:** Either implement backend support or remove table definitions.

---

## Category 4: Backend Bugs

### TD-BUG-01: `evaluate_code()` Argument Mismatch 🔴
**Location:** `app/routes/interview.py:521-526`  
**Description:** Route calls `gemini_service.evaluate_code(question_text, code, language, interview_type)` but the method signature is `evaluate_code(self, code, language, question)`. Arguments are in wrong order and there's an extra argument.  
**Impact:** Code evaluation returns wrong results or fails silently (fallback returns fixed scores).  
**Remediation:** Fix argument order in the route call.

### TD-BUG-02: `generate_coding_question()` Argument Mismatch 🟠
**Location:** `app/routes/interview.py:692`  
**Description:** Route calls `generate_coding_question(interview_type, difficulty, topic)` but method signature is `generate_coding_question(self, topic, difficulty)`. Extra argument, wrong order.  
**Impact:** Practice coding route generates wrong questions or hits fallback.  
**Remediation:** Fix argument order.

### TD-BUG-03: `generate_follow_up_question()` Type Mismatch 🟠
**Location:** `app/routes/interview.py:450`  
**Description:** Route passes `interview_type` (a string) as the third argument where the method expects `evaluation` (a dict).  
**Impact:** Follow-up generation always uses fallback because `evaluation.get('score', 0)` fails on a string.  
**Remediation:** Pass proper evaluation dict.

### TD-BUG-04: `security/check` Missing Key 🟠
**Location:** `app/routes/interview.py:612`  
**Description:** Route accesses `cheating_detection['confidence']` but `SecurityService.detect_cheating()` never returns a `confidence` key.  
**Impact:** Will throw `KeyError` and return 500.  
**Remediation:** Add `confidence` to SecurityService return, or remove reference.

### TD-BUG-05: `security/report` Missing Method 🔴
**Location:** `app/routes/interview.py:657`  
**Description:** Route calls `security_service.get_security_report(session_id)` but `SecurityService` has no such method.  
**Impact:** Endpoint always returns 500.  
**Remediation:** Implement the method or remove the endpoint.

---

## Category 5: Frontend Issues

### TD-FE-01: All Analytics Data Hardcoded 🟠
**Location:** `dashboard/page.tsx`, `analytics/page.tsx`, `practice/page.tsx`  
**Description:** Three major screens display entirely fabricated data. Dashboard has inline mock session arrays, analytics has hardcoded chart data, practice has mock questions.  
**Impact:** Users see fake data. The app appears functional but is not.  
**Remediation:** Connect to real backend data sources.

### TD-FE-02: Fake Code Execution 🟠
**Location:** `enhanced-code-editor.tsx:262-294`, `api/execute/route.ts`  
**Description:** "Run Code" button executes `setTimeout(1-3s)` and shows hardcoded "Result: 9" regardless of code or language. The API route returns a static string.  
**Impact:** Users believe their code is being executed. It is not.  
**Remediation:** Integrate a real sandboxed code execution service (e.g., Judge0, Piston, or custom Docker runner).

### TD-FE-03: Auth Crash Without Config 🟡
**Location:** `login/page.tsx:12`, `signup/page.tsx:7`  
**Description:** `getBrowserSupabaseClient()` returns `null` when env vars missing, but login/signup pages call `.auth.signInWithPassword()` directly on the result without null checking.  
**Impact:** Page crash if Supabase not configured.  
**Remediation:** Add null checks and display configuration error.

### TD-FE-04: Stale Dependencies 🟡
**Location:** `frontend/package.json`  
**Description:** Dependencies include `@remix-run/react`, `@sveltejs/kit`, `svelte`, `vue`, `vue-router` — frameworks not used by this Next.js app.  
**Impact:** Bloated `node_modules`, potential dependency conflicts.  
**Remediation:** Remove unused framework dependencies.

### TD-FE-05: Broken Lockfile 🟡
**Location:** `frontend/pnpm-lock.yaml`  
**Description:** File is only 96 bytes — far too small to be a valid lockfile.  
**Impact:** Non-reproducible builds, dependency resolution issues.  
**Remediation:** Delete and regenerate with `pnpm install`.

---

## Category 6: Code Quality

### TD-CQ-01: Duplicated JSON Extraction 🟡
**Location:** `app/services/gemini_service.py` — appears 5 times identically  
**Description:** The same 8-line JSON extraction pattern (searching for ` ```json ` markers) is copy-pasted in every method.  
**Impact:** Maintenance burden, inconsistent behavior if one copy is modified.  
**Remediation:** Extract into a shared `_extract_json()` helper method.

### TD-CQ-02: Silent Fallback Masking 🟠
**Location:** `app/services/gemini_service.py` — every method  
**Description:** On any exception, methods return hardcoded response dicts with `score: 70` and `model_used: "fallback"`. The consumer has no way to distinguish a real 70-score evaluation from a total failure.  
**Impact:** Bugs are hidden, users receive fabricated scores.  
**Remediation:** Raise exceptions or use a distinct error response format that consumers can detect.

### TD-CQ-03: No Type Safety in Backend 🟡
**Location:** Throughout `app/`  
**Description:** No Pydantic models, no dataclasses, no TypedDicts. All data flows as untyped dicts. Type hints exist on method signatures but aren't enforced.  
**Impact:** Runtime errors from typos and missing keys.  
**Remediation:** Adopt Pydantic for request/response validation.

### TD-CQ-04: Missing Error Boundaries 🟡
**Location:** Frontend components  
**Description:** No React error boundaries. A crash in any component takes down the entire page.  
**Impact:** Poor user experience on errors.  
**Remediation:** Add error boundaries around major component sections.

---

## Category 7: DevOps & Infrastructure

### TD-OPS-01: No Container / Deployment Config 🟠
**Location:** Root directory  
**Description:** No Dockerfile, no docker-compose, no Kubernetes manifests, no Vercel config. Only a `deploy.py` script of unclear functionality.  
**Impact:** Cannot deploy reliably.  
**Remediation:** Create Dockerfile for backend, configure Vercel/similar for frontend.

### TD-OPS-02: No CI/CD Pipeline 🟠
**Location:** Root directory  
**Description:** No GitHub Actions, no GitLab CI, no test/lint/build automation.  
**Impact:** No automated quality gates.  
**Remediation:** Set up GitHub Actions for lint, test, and build on PR.

### TD-OPS-03: No Environment Configuration 🟡
**Location:** `config.py` (unused), `app/__init__.py`  
**Description:** Multi-environment config classes exist but aren't used. The app always uses development defaults.  
**Impact:** No production-safe configuration.  
**Remediation:** Wire `FLASK_ENV` to config selection in `create_app()`.

### TD-OPS-04: Local File Logging Only 🟡
**Location:** `app.py:17`  
**Description:** Logs written to `app.log` file only. No structured logging, no log aggregation, no monitoring.  
**Impact:** No observability in production.  
**Remediation:** Implement structured JSON logging with integration to a log aggregator.

---

## Summary by Severity

| Severity | Count | Categories |
|----------|-------|------------|
| 🔴 Critical | 4 | SEC-01, SEC-02, BUG-01, BUG-05 |
| 🟠 High | 14 | SEC-03, SEC-04, SEC-05, ARCH-01, ARCH-02, DATA-01, DATA-02, BUG-02, BUG-03, BUG-04, FE-01, FE-02, CQ-02, OPS-01, OPS-02 |
| 🟡 Medium | 14 | SEC-06, SEC-07, ARCH-03, ARCH-04, DATA-03, DATA-04, FE-03, FE-04, FE-05, CQ-01, CQ-03, CQ-04, OPS-03, OPS-04 |
| 🟢 Low | 1 | ARCH-05 |
| **Total** | **33** | |

---

## Immediate Action Items (Before Any Feature Work)

1. **Fix TD-SEC-01 + TD-SEC-02**: Implement backend auth — all other work is pointless without data integrity.
2. **Fix TD-BUG-01 + TD-BUG-05**: Fix crashing endpoints.
3. **Fix TD-ARCH-02**: Wire frontend to backend session creation.
4. **Fix TD-SEC-05**: Disable debug mode.
5. **Fix TD-DATA-02**: Fix question text storage.
