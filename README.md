# AI Interview Platform — Backend

A structured, typed Python backend for an AI-powered technical and behavioral interview platform. Built with Flask, Supabase (PostgreSQL), and Google Gemini structured generation.

---

## 🏗️ Architecture & Domain Organization

The backend is refactored around clean, explicit domain boundaries:

```
app/
├── api/             # HTTP transport layer (blueprints, validation, route controllers)
│   ├── interview.py     # Sessions, question delivery, answer submission, code execution
│   ├── intelligence.py  # Skill profiles, recommendations, activity status updates
│   ├── analytics.py     # Longitudinal metrics, regression slope, weakness clustering
│   └── logging.py       # Session event logging, anomaly reporting, health check
├── domain/          # Core business entities (framework-agnostic typed dataclasses)
│   └── __init__.py      # Session, Question, Evaluation, SkillEvidence, Recommendation, etc.
├── schemas/         # Pydantic validation schemas for API requests & responses
├── services/        # Orchestrators coordinating domain logic across modules
│   ├── orchestrator/    # Interview state machine, adaptive difficulty, question queue
│   └── supabase_service.py
├── repositories/    # Typed database access layer (PostgreSQL / Supabase)
├── ai/              # AI provider integration, prompts, and structured output parsing
│   ├── providers/       # Google Gemini provider with backoff and JSON schema modes
│   ├── schemas.py       # Pydantic schemas for AI output contracts
│   └── engine.py        # AssessmentEngine with execution telemetry & AIRun tracking
├── analytics/       # Longitudinal analytics engine
│   ├── methodology.py   # Statistical functions (regression, dispersion, DBSCAN-clustering, lift)
│   ├── models.py        # Typed analytics schemas
│   └── service.py       # LongitudinalAnalyticsService
├── security/        # Auth & integrity engine
│   ├── auth.py          # Supabase JWT extraction, caller identity, ownership verification
│   └── integrity.py     # Session integrity analysis and risk scoring
└── infrastructure/  # External adapters
    ├── supabase.py      # SupabaseClient singleton
    └── sandbox.py       # Subprocess-isolated code execution runner
```

---

## 🧩 Core Domain Concepts

| Concept | Purpose |
|---|---|
| `InterviewSession` | Stateful interview instance with status lifecycle, timing, and cumulative score. |
| `InterviewQuestion` | Contextual question tailored by role, skill focus, difficulty, and rubric. |
| `CandidateResponse` | Recorded candidate text or code answer. |
| `Evaluation` | Multi-dimensional scoring (accuracy, depth, problem solving, communication, evidence). |
| `SkillEvidence` | Fine-grained skill data points linked to responses and evaluations. |
| `CandidateSkillProfile` | Longitudinal Bayesian-style proficiency estimate per candidate and skill. |
| `Recommendation` | Targeted practice suggestions prioritizing candidate-specific weaknesses. |
| `IntegrityEvent` | Session telemetry anomalies (focus loss, cadence, paste) weighted for audit review. |
| `CodeSubmission` | Candidate source code submission for coding interview problems. |
| `ExecutionRun` | Sandboxed test execution result (stdout, stderr, exit code, execution time). |
| `AIRun` | Audit record of prompt, model, tokens, latency, and status for every AI call. |

---

## 🔒 Security Model

1. **Server-Side Identity**: Client-provided identity (`user_id`) in request bodies is never trusted. The verified user ID is extracted server-side from the Supabase JWT (`Authorization: Bearer <token>`).
2. **Resource Authorization**: Every resource lookup verifies session and user ownership before returning data.
3. **No Cross-User Access**: Accessing another user's session, questions, skill profile, or analytics returns HTTP 403.
4. **Environment Secrets**: Secrets (`SUPABASE_KEY`, `GEMINI_API_KEY`) are kept on the server. `FLASK_DEBUG` defaults to `False`.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- Supabase project
- Google Gemini API key

### 2. Installation
```bash
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Unix:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Database Migration
Apply the single authoritative migration file to your Supabase project SQL Editor:
```bash
001_authoritative_schema.sql
```
For schema details, see [`docs/DATABASE_ARCHITECTURE.md`](docs/DATABASE_ARCHITECTURE.md).

### 4. Environment Configuration
Copy `env.example` to `.env` and fill in credentials:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-service-role-key
GEMINI_API_KEY=your-gemini-api-key
FLASK_SECRET_KEY=change-in-production
FRONTEND_URL=http://localhost:3000
FLASK_DEBUG=false
```

### 5. Running the Application
```bash
python app.py
```
Backend runs by default on `http://127.0.0.1:5000`.

---

## 🧪 Testing

The test suite runs with `pytest` and covers analytics regression models, integrity scoring, authorization policies, route controllers, and domain models:

```bash
python -m pytest
```

Configuration is defined in [`pytest.ini`](pytest.ini).
