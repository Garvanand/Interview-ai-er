# Authentication & Authorization — Security Audit

> **Audit Date:** 2026-09-30  
> **Scope:** Full stack (Flask backend + Next.js frontend)  
> **Status:** ✅ Hardened

---

## Summary of Changes

This document records every authentication and authorization vulnerability found and its resolution.

---

## 1. Backend — `app/auth.py`

### Before
- File did not exist. No JWT validation middleware anywhere in the codebase.
- Every endpoint accepted `user_id` from the request body.
- Any client could impersonate any user by sending an arbitrary `user_id`.

### After
- **`require_auth` decorator** validates the Supabase JWT from `Authorization: Bearer <token>`.
- Identity (`g.user_id`, `g.user_email`) is set **only** from the verified token — never from request data.
- **`verify_session_ownership(session_id, user_id)`** checks that a session belongs to the requesting user before any session-scoped operation.
- **`verify_user_ownership(path_user_id)`** checks that a URL path `user_id` matches `g.user_id` from the token.
- Standardized 401/403 helpers: `unauthorized_response()`, `not_found_response()`.
- Machine-readable error codes: `AUTHENTICATION_REQUIRED`, `EMPTY_TOKEN`, `INVALID_TOKEN`, `AUTHENTICATION_FAILED`, `UNAUTHORIZED`.

---

## 2. Backend Route Audit

| Route | Auth Before | Auth After |
|-------|------------|------------|
| `POST /api/start_session` | ❌ None | ✅ `@require_auth`, user_id from token |
| `GET /api/get_question` | ❌ None | ✅ `@require_auth` + session ownership |
| `POST /api/submit_answer` | ❌ None | ✅ `@require_auth` + session ownership |
| `POST /api/submit_code` | ❌ None | ✅ `@require_auth` + session ownership |
| `POST /api/run_code` | ❌ None | ✅ `@require_auth` |
| `GET /api/session/<id>` | ❌ None | ✅ `@require_auth` + session ownership |
| `GET /api/session/<id>/state` | ❌ None | ✅ `@require_auth` + session ownership |
| `POST /api/end_session/<id>` | ❌ None | ✅ `@require_auth` + session ownership |
| `GET /api/user/<id>/sessions` | ❌ None | ✅ `@require_auth` + path user_id check |
| `POST /api/follow_up_question` | ❌ None | ✅ `@require_auth` |
| `POST /api/security/check` | ❌ None | ✅ `@require_auth` + session ownership |
| `GET /api/security/report/<id>` | ❌ None | ✅ `@require_auth` + session ownership |
| `POST /api/practice/coding` | ❌ None | ✅ `@require_auth` |
| `POST /api/log_event` | ❌ None | ✅ `@require_auth` + session ownership |
| `POST /api/log_anomaly` | ❌ None | ✅ `@require_auth` + session ownership |
| `GET /api/events/<id>` | ❌ None | ✅ `@require_auth` + session ownership |
| `GET /api/anomalies/<id>` | ❌ None | ✅ `@require_auth` + session ownership |
| `GET /api/intelligence/skills/<uid>` | ❌ None | ✅ `@require_auth` + path user_id check |
| `GET /api/intelligence/recommendations/<uid>` | ❌ None | ✅ `@require_auth` + path user_id check |
| `POST /api/intelligence/recommendations/<uid>/generate` | ❌ None | ✅ `@require_auth` + path user_id check |
| `PATCH /api/intelligence/recommendations/<id>/status` | ❌ None | ✅ `@require_auth` + recommendation ownership |
| `GET /api/analytics/<uid>` | ❌ None | ✅ `@require_auth` + path user_id check |
| `GET /api/analytics/filter-options/<uid>` | ❌ None | ✅ `@require_auth` + path user_id check |
| `GET /api/health` | ✅ Public | ✅ Unchanged |
| `GET /api/metrics` | ✅ Public | ✅ Unchanged |

---

## 3. Frontend Route Guard — `middleware.ts`

### Before
- If `SUPABASE_URL` or `SUPABASE_KEY` env vars were absent, middleware passed **all requests** through without authentication.
- Catch block silently allowed access on error.
- Authenticated users were not redirected away from `/login` / `/signup`.

### After
- **Fail-secure**: If Supabase is not configured, protected routes redirect to `/login` with `?reason=auth_not_configured`.
- **Fail-secure**: If middleware throws, protected routes redirect to `/login` — never grant access.
- **`getUser()`** is used (server-side JWT verification), not `getSession()` (local cookie only).
- Authenticated users visiting `/login` or `/signup` are redirected to `/dashboard`.
- Post-login redirect: the intended path is preserved in `?redirectTo=` and restored after login.

---

## 4. Frontend Auth State — `hooks/use-auth.ts`

### Before
- No centralized auth hook. Every page independently called `getBrowserSupabaseClient().auth.getUser()`.
- Dashboard, analytics, and interview pages all fell back to a hardcoded demo UUID (`00000000-0000-0000-0000-000000000001`) when unauthenticated.
- Interview page fell back to `"guest_candidate"` string which would fail backend UUID validation.

### After
- **`useAuth` hook** is the single source of truth for auth state.
- `userId` is `null` when unauthenticated — never a hardcoded fallback.
- Pages using `useAuth({ redirectIfUnauthenticated: true })` automatically redirect to `/login`.
- Subscribes to `onAuthStateChange` to stay in sync across tab events.
- `signOut()` function calls `supabase.auth.signOut()` and redirects to `/login`.

---

## 5. Navigation — `components/navigation.tsx`

### Before
- Static nav links shown to all users regardless of auth state.
- No logout button.
- No user identity display.

### After
- Protected nav items (Dashboard, Interview, Analytics, History, Practice, IDE) are **only shown to authenticated users**.
- Auth state managed via `useAuth` hook.
- Logout button triggers `signOut()` and redirects to `/login`.
- Authenticated user's email is displayed in the navbar.
- Unauthenticated users see Sign in / Get Started buttons.

---

## 6. Login & Signup Pages

### Before
- Would crash if Supabase was not configured (uncaught null reference on `supabase.auth`).
- No password length validation on signup.
- No redirect for already-authenticated users.
- No user feedback for success state on signup.
- Generic error display.

### After
- **Supabase-not-configured fallback**: Both pages render a clear warning instead of crashing.
- Already-authenticated users are redirected to `/dashboard` on mount.
- Signup enforces minimum password length (8 chars) both client-side and via Supabase.
- Login reads `?redirectTo=` param and restores the intended destination after auth.
- Proper loading states with spinner, accessible `id` attributes on all inputs.
- Clear success state on signup with email confirmation message.

---

## 7. Pages Fixed

| Page | Issue | Fix |
|------|-------|-----|
| `/dashboard` | Hardcoded demo UUID fallback | Uses `useAuth` — shows error if unauthenticated |
| `/analytics` | Hardcoded demo UUID fallback | Uses `useAuth` — blocks load until auth resolves |
| `/interview` | Falls back to `"guest_candidate"` | Uses `useAuth` — rejects start if not authenticated |
| `/history` | No error if unauthenticated | No changes needed — already used `supabase.auth.getUser()` correctly |

---

## 8. Authorization Test Coverage

**File:** `tests/test_authorization.py`

| Test | Scenario | Status |
|------|----------|--------|
| `test_missing_auth_header_returns_401` (×10) | Every protected endpoint, no auth header | ✅ PASS |
| `test_malformed_token_format_returns_401` | `Basic` scheme instead of `Bearer` | ✅ PASS |
| `test_empty_bearer_token_returns_401` | `Bearer ` with no token | ✅ PASS |
| `test_invalid_token_content_returns_401` | Supabase returns `user=None` | ✅ PASS |
| `test_cross_user_session_access_returns_403` | User A reads User B's session | ✅ PASS |
| `test_cross_user_session_state_access_returns_403` | User A reads User B's state | ✅ PASS |
| `test_cross_user_end_session_returns_403` | User A ends User B's session | ✅ PASS |
| `test_own_session_access_proceeds` | User A reads their own session | ✅ PASS |
| `test_user_id_path_mismatch_on_sessions_returns_403` | `/user/other/sessions` | ✅ PASS |
| `test_intelligence_skills_path_mismatch_returns_403` | `/intelligence/skills/other` | ✅ PASS |
| `test_analytics_path_mismatch_returns_403` | `/analytics/other` | ✅ PASS |
| `test_401_response_shape` | 401 body structure validation | ✅ PASS |
| `test_403_response_shape` | 403 body structure validation | ✅ PASS |

**Total: 29/29 tests passing** (including analytics + integrity suite)

---

## 9. Residual Risks

| Risk | Status | Notes |
|------|--------|-------|
| Supabase RLS enforcement | ⚠️ Partial | Backend uses service role key; RLS still not enforced at DB layer. This is acceptable since backend auth is now the enforcing layer. If service key is leaked, RLS would need to be enforced too. |
| Recommendation ownership by ID | ⚠️ Partial | `PATCH /recommendations/<id>/status` and `POST /recommendations/<id>/evaluate_outcome` check that the recommendation's `user_id` matches `g.user_id` — but this requires a DB lookup. Currently mocked in tests. |
| Token revocation | ℹ️ Information | Supabase JWTs are valid until expiry. If a user needs to be immediately blocked, the Supabase admin API must be used. This is a platform-level limitation, not a code issue. |
| CORS | ⚠️ Review | CORS is configured with `FRONTEND_URL` allowlist. Ensure this is set correctly in production to prevent cross-origin API access. |
