# Interview Orchestrator & State Machine

## 1. Overview
The **Interview Orchestrator** transforms the application from independent question generation into a **stateful, adaptive, backend-authoritative assessment engine**.

The backend serves as the single source of truth for:
- State Machine Phase (`INITIALIZING`, `QUESTIONING`, `EVALUATING`, `FOLLOW_UP`, `DIFFICULTY_ADJUSTMENT`, `FINAL_ASSESSMENT`, `COMPLETED`, `FAILED`)
- Adaptive Difficulty (`beginner`, `intermediate`, `advanced`)
- Target Role & Competency Matrix
- Current Skill Focus & Balanced Skill Coverage
- Question History & Duplicate Prevention
- Candidate Performance & Skill Signal Tracking
- Targeted Weakness Probing via Structured Follow-ups
- Session Policy & Time Budget Enforcement

---

## 2. Interview State Machine

```mermaid
stateDiagram-v2
    [*] --> INITIALIZING: Session Started
    INITIALIZING --> QUESTIONING: Initial Role Question Selected
    INITIALIZING --> FAILED: Invalid Config / Auth Error

    QUESTIONING --> EVALUATING: Candidate Submits Answer / Code
    QUESTIONING --> FINAL_ASSESSMENT: Question Budget / Time Limit Reached
    QUESTIONING --> FAILED: Fatal Error

    EVALUATING --> DIFFICULTY_ADJUSTMENT: AI Telemetry & Rubric Scored
    EVALUATING --> FAILED: Model Failure / Unrecoverable

    DIFFICULTY_ADJUSTMENT --> FOLLOW_UP: Weakness Detected (Score < 65)
    DIFFICULTY_ADJUSTMENT --> QUESTIONING: Next Skill Question Selected
    DIFFICULTY_ADJUSTMENT --> FINAL_ASSESSMENT: Max Questions Limit Reached
    DIFFICULTY_ADJUSTMENT --> COMPLETED: Interview Concluded

    FOLLOW_UP --> EVALUATING: Follow-up Answer Submitted
    FOLLOW_UP --> FINAL_ASSESSMENT: Budget Exhausted

    FINAL_ASSESSMENT --> COMPLETED: Holistic Synthesis & Ratings Generated
    COMPLETED --> [*]
    FAILED --> [*]
```

---

## 3. Sequence Diagram: Stateful Adaptive Loop

The diagram below details the end-to-end communication flow between the Frontend, the Flask API Routes, the `InterviewOrchestrator`, the `AssessmentEngine` (Google GenAI), and the `Supabase` database:

```mermaid
sequenceDiagram
    autonumber
    actor Candidate as Candidate (Frontend)
    participant API as Flask API Route
    participant Orch as Interview Orchestrator
    participant AI as Assessment Engine (GenAI)
    participant DB as Supabase DB

    %% 1. Session Initialization
    Note over Candidate, DB: 1. Session Initialization
    Candidate->>API: POST /api/start_session (user_id, role)
    API->>DB: create_session(user_id, role)
    DB-->>API: session_id
    API->>Orch: initialize_session(session_id, user_id, role)
    Orch->>DB: log_event("orchestrator_initialized", metadata)
    API-->>Candidate: { session_id, phase: "INITIALIZING", skills, difficulty }

    %% 2. Question Generation with Skill Balance & Duplicate Prevention
    Note over Candidate, DB: 2. Stateful Question Retrieval
    Candidate->>API: GET /api/get_question?session_id=...
    API->>Orch: get_next_question(session_id)
    Orch->>Orch: Check Policy (budget/max questions)
    Orch->>Orch: Select least-tested skill (Balanced Distribution)
    Orch->>Orch: Collect past questions (Duplicate Prevention)
    Orch->>Orch: Transition to QUESTIONING
    Orch->>AI: generate_question(role, skill, difficulty, exclusions)
    AI-->>Orch: Question Schema
    Orch->>DB: store_question(session_id, question_text, ...)
    Orch->>DB: log_event("state_transition", QUESTIONING)
    Orch-->>API: Question Payload
    API-->>Candidate: { question_id, question_text, skill_focus, difficulty, phase }

    %% 3. Submission & Evaluation
    Note over Candidate, DB: 3. Answer Submission & Evaluation
    Candidate->>API: POST /api/submit_answer (session_id, question_id, answer_text)
    API->>Orch: record_and_evaluate_answer(session_id, question_id, answer_text)
    Orch->>Orch: Transition to EVALUATING
    Orch->>AI: evaluate_answer(question, answer, schema)
    AI-->>Orch: AnswerEvaluation (score, strengths, weaknesses, rubric)
    Orch->>DB: store_answer(question_id, score, evaluation_details)
    Orch->>Orch: Update SkillSignal for current skill

    %% 4. Difficulty Adaptation & Follow-up Discovery
    Note over Candidate, DB: 4. Difficulty Adaptation & Probing
    Orch->>Orch: Transition to DIFFICULTY_ADJUSTMENT
    alt Score >= 75 (Consecutive Strong >= 2)
        Orch->>Orch: Difficulty Level UP (e.g., intermediate -> advanced)
        Orch->>DB: log_event("difficulty_adjusted", { to: "advanced" })
    else Score < 50 (Consecutive Weak >= 2)
        Orch->>Orch: Difficulty Level DOWN (e.g., intermediate -> beginner)
        Orch->>DB: log_event("difficulty_adjusted", { to: "beginner" })
    end

    opt Score < 65 & Weaknesses Present
        Orch->>Orch: Register FollowUpOpportunity for specific gap
    end

    Orch->>DB: update_session_score(session_id, avg_score)
    Orch-->>API: Evaluation Result + Updated Phase + Difficulty
    API-->>Candidate: { evaluation, session_score, current_difficulty, current_phase }

    %% 5. Targeted Follow-Up Flow
    opt When FollowUpOpportunity Exists
        Note over Candidate, DB: 5. Targeted Follow-up Probing
        Candidate->>API: GET /api/get_question?session_id=...
        API->>Orch: get_next_question(session_id)
        Orch->>Orch: Transition to FOLLOW_UP
        Orch->>AI: generate_follow_up_question(parent_q, weakness, skill)
        AI-->>Orch: Targeted Question Schema
        Orch->>DB: store_question(..., is_follow_up=True)
        Orch-->>API: Follow-up Question Payload
        API-->>Candidate: { question_text, is_follow_up: true, phase: "FOLLOW_UP" }
    end

    %% 6. Final Assessment
    Note over Candidate, DB: 6. Session Finalization
    Candidate->>API: POST /api/end_session (session_id)
    API->>Orch: finalize_interview(session_id)
    Orch->>Orch: Transition to FINAL_ASSESSMENT
    Orch->>AI: synthesize_session(full_transcript_summary)
    AI-->>Orch: SessionSynthesis (rating, summary, strengths, red_flags)
    Orch->>Orch: Transition to COMPLETED
    Orch->>DB: end_session(session_id, final_score)
    Orch->>DB: log_event("interview_orchestrator_completed", assessment)
    Orch-->>API: Final Synthesis Result
    API-->>Candidate: { final_score, assessment, phase: "COMPLETED", is_completed: true }
```

---

## 4. Key Orchestration Algorithms

### 4.1 Balanced Skill Distribution
For each target role, the orchestrator tracks a `SkillSignal` per competency:
- `Software Engineer`: Data Structures & Algorithms, System Architecture, API Design, Concurrency, Testing & Reliability.
- `Data Scientist`: Statistics, Machine Learning, Data Pipelines/SQL, Feature Engineering, Evaluation & Ethics.
- `Product Manager`: Strategy, Metrics & Experimentation, User Empathy, Prioritization, Technical Communication.
- `DevOps Engineer`: CI/CD, Containerization/Kubernetes, Infrastructure as Code, Observability, Cloud Security.

**Selection Rule**:
The next skill focus is selected using `min(skills_distribution.values(), key=lambda s: (s.questions_count, len(s.scores)))`. This guarantees that questions cycle evenly through the curriculum rather than repeatedly testing the same domain.

### 4.2 Adaptive Difficulty Engine
Difficulty is modeled across three levels: `beginner` <-> `intermediate` <-> `advanced`.
- Initial state is set to `intermediate`.
- Two consecutive answers with `score >= 75` elevate difficulty to `advanced`.
- Two consecutive answers with `score < 50` lower difficulty to `beginner`.
- Any middle score (50–74) resets the consecutive streak, preventing oscillation.
- Difficulty adjustments are strictly bounded: upper bound at `advanced`, lower bound at `beginner`.

### 4.3 Duplicate Question Prevention
Duplicate questions degrade candidate experience and distort assessments.
1. The orchestrator maintains an authoritative history of question texts (`questions_asked`).
2. When requesting questions from the model, the previous question texts are injected into the negative constraint rubric.
3. Before storing any question, the normalized alphanumeric representation is compared against all previously asked questions.
4. If a near-identical question is produced, the orchestrator rejects it and generates an alternative scenario.

### 4.4 Targeted Follow-ups vs. Generic Follow-ups
Unlike generic prompts ("Can you elaborate?"), the orchestrator tracks candidate weaknesses:
- When a candidate scores `< 65` on a question, the top weakness (e.g., "Failed to explain lock contention") is extracted.
- A `FollowUpOpportunity` is queued targeting that specific flaw.
- The follow-up question specifically probes the edge case, tradeoff, or failure scenario where the candidate faltered.

### 4.5 Backend Authoritative State
- State is managed and stored in backend memory with full reconstitution capability from the Supabase `sessions`, `questions`, and `logs` tables.
- Frontend clients query `/api/session/<session_id>/state` to retrieve current phase, skill progress, and metrics.
- All state transitions persist structured audit records in the Supabase `logs` table with event type `state_transition`.
