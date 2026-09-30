-- Authoritative Schema Migration
-- Consolidates previous overlapping migrations into a clean, normalized relational model.

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. PROFILES (Extend auth.users)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- Handle existing sessions table -> interview_sessions
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sessions') AND 
       NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'interview_sessions') THEN
        ALTER TABLE sessions RENAME TO interview_sessions;
        ALTER TABLE interview_sessions RENAME CONSTRAINT sessions_pkey TO interview_sessions_pkey;
    END IF;
END $$;

-- 2. INTERVIEW_SESSIONS
CREATE TABLE IF NOT EXISTS interview_sessions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    interview_type VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    end_time TIMESTAMP WITH TIME ZONE,
    score DECIMAL(5,2) DEFAULT 0.00,
    session_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
ALTER TABLE interview_sessions ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_interview_sessions_user_id ON interview_sessions(user_id);

-- Handle existing questions table -> interview_questions
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'questions') AND 
       NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'interview_questions') THEN
        ALTER TABLE questions RENAME TO interview_questions;
        ALTER TABLE interview_questions RENAME CONSTRAINT questions_pkey TO interview_questions_pkey;
    END IF;
END $$;

-- 3. INTERVIEW_QUESTIONS
CREATE TABLE IF NOT EXISTS interview_questions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    session_id UUID REFERENCES interview_sessions(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    question_type VARCHAR(100) DEFAULT 'technical',
    difficulty VARCHAR(20) DEFAULT 'medium',
    expected_format VARCHAR(100),
    question_order INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
ALTER TABLE interview_questions ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_interview_questions_session_id ON interview_questions(session_id);

-- 4. RESPONSES
CREATE TABLE IF NOT EXISTS responses (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    question_id UUID REFERENCES interview_questions(id) ON DELETE CASCADE,
    response_text TEXT,
    audio_url VARCHAR(255),
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
ALTER TABLE responses ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_responses_question_id ON responses(question_id);

-- 5. EVALUATIONS
CREATE TABLE IF NOT EXISTS evaluations (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    response_id UUID REFERENCES responses(id) ON DELETE CASCADE,
    score DECIMAL(5,2),
    feedback TEXT,
    evaluation_details JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'COMPLETED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
ALTER TABLE evaluations ENABLE ROW LEVEL SECURITY;

-- 6. SKILL_EVIDENCE
CREATE TABLE IF NOT EXISTS skill_evidence (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    evaluation_id UUID REFERENCES evaluations(id) ON DELETE CASCADE,
    skill_name VARCHAR(150) NOT NULL,
    signal_strength DECIMAL(5,2),
    evidence_text TEXT,
    confidence VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
ALTER TABLE skill_evidence ENABLE ROW LEVEL SECURITY;

-- Normalize existing data from interview_questions to responses and evaluations
DO $$
BEGIN
    -- If the old columns still exist
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'interview_questions' AND column_name = 'answer_text') THEN
        
        -- Insert into responses
        INSERT INTO responses (id, question_id, response_text, submitted_at, created_at, updated_at)
        SELECT 
            uuid_generate_v4(), 
            id, 
            answer_text, 
            updated_at, 
            created_at, 
            updated_at
        FROM interview_questions 
        WHERE answer_text IS NOT NULL;
        
        -- Insert into evaluations using CTE to match response_id
        INSERT INTO evaluations (response_id, score, feedback, evaluation_details)
        SELECT 
            r.id, 
            q.evaluation_score, 
            q.evaluation_feedback, 
            q.evaluation_details
        FROM interview_questions q
        JOIN responses r ON r.question_id = q.id
        WHERE q.evaluation_score IS NOT NULL OR q.evaluation_feedback IS NOT NULL;
        
        -- Clean up old columns from interview_questions
        ALTER TABLE interview_questions DROP COLUMN IF EXISTS answer_text;
        ALTER TABLE interview_questions DROP COLUMN IF EXISTS evaluation_score;
        ALTER TABLE interview_questions DROP COLUMN IF EXISTS evaluation_feedback;
        ALTER TABLE interview_questions DROP COLUMN IF EXISTS evaluation_details;
        ALTER TABLE interview_questions DROP COLUMN IF EXISTS code_text;
        ALTER TABLE interview_questions DROP COLUMN IF EXISTS programming_language;
        ALTER TABLE interview_questions DROP COLUMN IF EXISTS code_evaluation_score;
        ALTER TABLE interview_questions DROP COLUMN IF EXISTS code_evaluation_details;
    END IF;
END $$;

-- 7. CANDIDATE_SKILL_PROFILES
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'skill_profiles') AND 
       NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'candidate_skill_profiles') THEN
        ALTER TABLE skill_profiles RENAME TO candidate_skill_profiles;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS candidate_skill_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    skill_name VARCHAR(150) NOT NULL,
    estimated_proficiency DECIMAL(5,2) DEFAULT 0.00,
    confidence VARCHAR(50) DEFAULT 'insufficient evidence',
    evidence_count INTEGER DEFAULT 0,
    recent_performance DECIMAL(5,2) DEFAULT 0.00,
    historical_performance DECIMAL(5,2) DEFAULT 0.00,
    improvement_trend VARCHAR(50) DEFAULT 'neutral',
    last_evaluated_timestamp TIMESTAMP WITH TIME ZONE,
    evidence_history JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
ALTER TABLE candidate_skill_profiles ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_candidate_skill_profiles_user_id ON candidate_skill_profiles(user_id);

-- 8. RECOMMENDATIONS
CREATE TABLE IF NOT EXISTS recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES interview_sessions(id) ON DELETE SET NULL,
    target_skill VARCHAR(150) NOT NULL,
    strategy VARCHAR(50) NOT NULL,
    reason TEXT NOT NULL,
    evidence JSONB DEFAULT '{}',
    recommended_activity JSONB DEFAULT '{}',
    priority VARCHAR(20) NOT NULL,
    expected_learning_objective TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    baseline_proficiency DECIMAL(5,2) DEFAULT 0.00,
    post_outcome_proficiency DECIMAL(5,2),
    outcome_delta DECIMAL(5,2),
    outcome_assessment VARCHAR(50)
);
ALTER TABLE recommendations ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_recommendations_user_id ON recommendations(user_id);

-- 9. PRACTICE_SESSIONS
CREATE TABLE IF NOT EXISTS practice_sessions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    interview_type VARCHAR(100) NOT NULL,
    topic VARCHAR(100) NOT NULL,
    difficulty VARCHAR(20) DEFAULT 'medium',
    questions_attempted INTEGER DEFAULT 0,
    questions_correct INTEGER DEFAULT 0,
    total_score DECIMAL(5,2) DEFAULT 0.00,
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    end_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
ALTER TABLE practice_sessions ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_practice_sessions_user_id ON practice_sessions(user_id);

-- 10. CODE_SUBMISSIONS
CREATE TABLE IF NOT EXISTS code_submissions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    question_id UUID REFERENCES interview_questions(id) ON DELETE CASCADE,
    code_text TEXT NOT NULL,
    programming_language VARCHAR(50) NOT NULL,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
ALTER TABLE code_submissions ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_code_submissions_question_id ON code_submissions(question_id);

-- 11. EXECUTION_RUNS
CREATE TABLE IF NOT EXISTS execution_runs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    code_submission_id UUID REFERENCES code_submissions(id) ON DELETE CASCADE,
    execution_time_ms INTEGER,
    memory_usage_kb INTEGER,
    stdout TEXT,
    stderr TEXT,
    exit_code INTEGER,
    test_cases_passed INTEGER DEFAULT 0,
    total_test_cases INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'COMPLETED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
ALTER TABLE execution_runs ENABLE ROW LEVEL SECURITY;

-- Fix old code_submissions schema and migrate data
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'code_submissions' AND column_name = 'evaluation_score') THEN
        -- Move execution details to execution_runs
        INSERT INTO execution_runs (code_submission_id, execution_time_ms, memory_usage_kb, test_cases_passed, total_test_cases)
        SELECT id, execution_time_ms, memory_usage_kb, test_cases_passed, total_test_cases
        FROM code_submissions;
        
        ALTER TABLE code_submissions DROP COLUMN IF EXISTS evaluation_score;
        ALTER TABLE code_submissions DROP COLUMN IF EXISTS evaluation_details;
        ALTER TABLE code_submissions DROP COLUMN IF EXISTS execution_time_ms;
        ALTER TABLE code_submissions DROP COLUMN IF EXISTS memory_usage_kb;
        ALTER TABLE code_submissions DROP COLUMN IF EXISTS test_cases_passed;
        ALTER TABLE code_submissions DROP COLUMN IF EXISTS total_test_cases;
        ALTER TABLE code_submissions DROP COLUMN IF EXISTS session_id; -- Normalized via question_id
    END IF;
END $$;

-- 12. SESSION_EVENTS
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'logs') AND 
       NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'session_events') THEN
        ALTER TABLE logs RENAME TO session_events;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS session_events (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    session_id UUID REFERENCES interview_sessions(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
ALTER TABLE session_events ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_session_events_session_id ON session_events(session_id);

DO $$
BEGIN
    -- Rename details to event_data if it exists
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'session_events' AND column_name = 'details') THEN
        ALTER TABLE session_events RENAME COLUMN details TO event_data;
    END IF;
END $$;

-- 13. INTEGRITY_EVENTS
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'security_events') AND 
       NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'integrity_events') THEN
        ALTER TABLE security_events RENAME TO integrity_events;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS integrity_events (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    session_id UUID REFERENCES interview_sessions(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) DEFAULT 'medium',
    confidence DECIMAL(5,2) DEFAULT 0.00,
    evidence_details JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
ALTER TABLE integrity_events ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_integrity_events_session_id ON integrity_events(session_id);

DO $$
BEGIN
    -- Merge anomalies into integrity_events
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'anomalies') THEN
        INSERT INTO integrity_events (session_id, event_type, severity, evidence_details, timestamp, created_at)
        SELECT session_id, anomaly_type, severity, details, timestamp, created_at
        FROM anomalies;
        
        DROP TABLE anomalies;
    END IF;
    
    -- Rename columns if migrating from security_events
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'integrity_events' AND column_name = 'security_level') THEN
        ALTER TABLE integrity_events RENAME COLUMN security_level TO severity;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'integrity_events' AND column_name = 'confidence_score') THEN
        ALTER TABLE integrity_events RENAME COLUMN confidence_score TO confidence;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'integrity_events' AND column_name = 'details') THEN
        ALTER TABLE integrity_events RENAME COLUMN details TO evidence_details;
    END IF;
END $$;

-- 14. AI_RUNS
CREATE TABLE IF NOT EXISTS ai_runs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    session_id UUID REFERENCES interview_sessions(id) ON DELETE CASCADE,
    prompt_name VARCHAR(100),
    model_version VARCHAR(100),
    latency_ms INTEGER,
    input_tokens INTEGER,
    output_tokens INTEGER,
    status VARCHAR(20) DEFAULT 'COMPLETED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
ALTER TABLE ai_runs ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_ai_runs_session_id ON ai_runs(session_id);

-- Update trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Re-apply triggers to the new normalized tables
DROP TRIGGER IF EXISTS update_responses_updated_at ON responses;
CREATE TRIGGER update_responses_updated_at BEFORE UPDATE ON responses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_evaluations_updated_at ON evaluations;
CREATE TRIGGER update_evaluations_updated_at BEFORE UPDATE ON evaluations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Clean up obsolete columns from interview_sessions
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'interview_sessions' AND column_name = 'security_score') THEN
        ALTER TABLE interview_sessions DROP COLUMN security_score;
        ALTER TABLE interview_sessions DROP COLUMN security_events_count;
        ALTER TABLE interview_sessions DROP COLUMN last_security_check;
    END IF;
END $$;
