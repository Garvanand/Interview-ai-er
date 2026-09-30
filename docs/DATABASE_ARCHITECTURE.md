# Database Architecture

This document defines the authoritative database architecture for the AI Interview Platform. The new architecture resolves inconsistencies from overlapping migrations and establishes a clean relational model optimized for the AI intelligence layer.

## Authoritative Migration Strategy

Instead of relying on fragmented schema scripts (`database_schema.sql`, `database_migration.sql`, `migrate_database.sql`), this project now uses a unified relational model. The transition is designed to be migration-safe, preserving existing data while normalizing entities that were previously merged.

## Relational Model & Entity Relationships

The schema is built on top of Supabase/PostgreSQL. It uses `uuid` for primary keys, enforces Row Level Security (RLS) on all tables, and utilizes JSONB for extensible metadata.

### 1. `profiles`
Extends Supabase's `auth.users` to store candidate-specific information.
- **id** (UUID, PK, references `auth.users(id)`)
- **first_name**, **last_name** (VARCHAR)
- **created_at**, **updated_at** (TIMESTAMPTZ)

### 2. `interview_sessions`
Represents a single interview session (stateful orchestrator).
- **id** (UUID, PK)
- **user_id** (UUID, FK `profiles.id`)
- **interview_type** (VARCHAR) (e.g., 'Software Engineer')
- **status** (VARCHAR) (INITIALIZING, QUESTIONING, EVALUATING, COMPLETED, FAILED)
- **start_time**, **end_time** (TIMESTAMPTZ)
- **session_metadata** (JSONB) - For difficulty, target role, current phase.
- **created_at**, **updated_at** (TIMESTAMPTZ)

### 3. `interview_questions`
The questions presented during a session.
- **id** (UUID, PK)
- **session_id** (UUID, FK `interview_sessions.id`)
- **question_text** (TEXT)
- **question_type** (VARCHAR) (e.g., technical, behavioral, coding)
- **difficulty** (VARCHAR)
- **expected_format** (VARCHAR)
- **question_order** (INTEGER)
- **created_at**, **updated_at** (TIMESTAMPTZ)

### 4. `responses`
The candidate's response to an interview question. Separated from `questions` table to allow multiple response attempts or structured data.
- **id** (UUID, PK)
- **question_id** (UUID, FK `interview_questions.id`)
- **response_text** (TEXT)
- **audio_url** (VARCHAR, nullable)
- **submitted_at** (TIMESTAMPTZ)
- **created_at**, **updated_at** (TIMESTAMPTZ)

### 5. `evaluations`
AI evaluation of a specific response.
- **id** (UUID, PK)
- **response_id** (UUID, FK `responses.id`)
- **score** (DECIMAL)
- **feedback** (TEXT)
- **evaluation_details** (JSONB)
- **status** (VARCHAR) (PENDING, COMPLETED, FAILED)
- **created_at**, **updated_at** (TIMESTAMPTZ)

### 6. `skill_evidence`
Discrete pieces of evidence derived from an evaluation.
- **id** (UUID, PK)
- **evaluation_id** (UUID, FK `evaluations.id`)
- **skill_name** (VARCHAR)
- **signal_strength** (DECIMAL)
- **evidence_text** (TEXT)
- **confidence** (VARCHAR)
- **created_at** (TIMESTAMPTZ)

### 7. `candidate_skill_profiles`
Aggregated longitudinal skill proficiency for a candidate.
- **id** (UUID, PK)
- **user_id** (UUID, FK `profiles.id`)
- **skill_name** (VARCHAR)
- **estimated_proficiency** (DECIMAL)
- **confidence** (VARCHAR)
- **evidence_count** (INTEGER)
- **recent_performance** (DECIMAL)
- **historical_performance** (DECIMAL)
- **improvement_trend** (VARCHAR)
- **last_evaluated_timestamp** (TIMESTAMPTZ)
- **created_at**, **updated_at** (TIMESTAMPTZ)

### 8. `recommendations`
Actionable next steps based on skill intelligence.
- **id** (UUID, PK)
- **user_id** (UUID, FK `profiles.id`)
- **session_id** (UUID, FK `interview_sessions.id`, nullable)
- **target_skill** (VARCHAR)
- **strategy** (VARCHAR)
- **reason** (TEXT)
- **recommended_activity** (JSONB)
- **priority** (VARCHAR)
- **expected_learning_objective** (TEXT)
- **status** (VARCHAR) (PENDING, COMPLETED, DISMISSED)
- **created_at**, **updated_at** (TIMESTAMPTZ)

### 9. `practice_sessions`
Lightweight practice mode tracking.
- **id** (UUID, PK)
- **user_id** (UUID, FK `profiles.id`)
- **topic** (VARCHAR)
- **difficulty** (VARCHAR)
- **questions_attempted** (INTEGER)
- **total_score** (DECIMAL)
- **start_time**, **end_time** (TIMESTAMPTZ)
- **created_at**, **updated_at** (TIMESTAMPTZ)

### 10. `code_submissions`
Source code submissions, separate from textual responses.
- **id** (UUID, PK)
- **question_id** (UUID, FK `interview_questions.id`)
- **code_text** (TEXT)
- **programming_language** (VARCHAR)
- **submitted_at** (TIMESTAMPTZ)
- **created_at** (TIMESTAMPTZ)

### 11. `execution_runs`
Records of sandboxed execution for a code submission.
- **id** (UUID, PK)
- **code_submission_id** (UUID, FK `code_submissions.id`)
- **execution_time_ms** (INTEGER)
- **memory_usage_kb** (INTEGER)
- **stdout** (TEXT)
- **stderr** (TEXT)
- **exit_code** (INTEGER)
- **test_cases_passed** (INTEGER)
- **total_test_cases** (INTEGER)
- **status** (VARCHAR)
- **created_at** (TIMESTAMPTZ)

### 12. `session_events`
General audit/telemetry logs for the session (UI events, visibility changes).
- **id** (UUID, PK)
- **session_id** (UUID, FK `interview_sessions.id`)
- **event_type** (VARCHAR)
- **event_data** (JSONB)
- **timestamp** (TIMESTAMPTZ)

### 13. `integrity_events`
Suspicious activities tracked during the session (Level 1, 2, 3 signals).
- **id** (UUID, PK)
- **session_id** (UUID, FK `interview_sessions.id`)
- **event_type** (VARCHAR)
- **severity** (VARCHAR)
- **confidence** (DECIMAL)
- **evidence_details** (JSONB)
- **timestamp** (TIMESTAMPTZ)

### 14. `ai_runs`
Audit trail of LLM inferences for determinism, billing, and debugging.
- **id** (UUID, PK)
- **session_id** (UUID, FK `interview_sessions.id`, nullable)
- **prompt_name** (VARCHAR)
- **model_version** (VARCHAR)
- **latency_ms** (INTEGER)
- **input_tokens** (INTEGER)
- **output_tokens** (INTEGER)
- **status** (VARCHAR)
- **created_at** (TIMESTAMPTZ)
