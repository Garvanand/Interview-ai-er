-- Migration script to add missing columns
-- Run this in your Supabase SQL editor

-- Add interview_type column to questions table
ALTER TABLE questions ADD COLUMN IF NOT EXISTS interview_type VARCHAR(100);

-- Add evaluation_feedback column to questions table
ALTER TABLE questions ADD COLUMN IF NOT EXISTS evaluation_feedback TEXT;

-- Add evaluation_details column to questions table
ALTER TABLE questions ADD COLUMN IF NOT EXISTS evaluation_details JSONB DEFAULT '{}';

-- Add status column to sessions table if not exists
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';

-- Add end_time column to sessions table if not exists
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS end_time TIMESTAMP WITH TIME ZONE;

-- Add code-related columns to questions table
ALTER TABLE questions ADD COLUMN IF NOT EXISTS code_text TEXT;
ALTER TABLE questions ADD COLUMN IF NOT EXISTS programming_language VARCHAR(50);
ALTER TABLE questions ADD COLUMN IF NOT EXISTS code_evaluation_score DECIMAL(5,2);
ALTER TABLE questions ADD COLUMN IF NOT EXISTS code_evaluation_details JSONB DEFAULT '{}';

-- Add security monitoring columns to sessions table
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS security_score DECIMAL(5,2) DEFAULT 100.0;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS security_events_count INTEGER DEFAULT 0;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS last_security_check TIMESTAMP WITH TIME ZONE;

-- Create new table for security events
CREATE TABLE IF NOT EXISTS security_events (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    security_level VARCHAR(20) DEFAULT 'low',
    confidence_score DECIMAL(5,2) DEFAULT 0.0,
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create new table for code submissions
CREATE TABLE IF NOT EXISTS code_submissions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    question_id UUID REFERENCES questions(id) ON DELETE CASCADE,
    code_text TEXT NOT NULL,
    programming_language VARCHAR(50) NOT NULL,
    evaluation_score DECIMAL(5,2),
    evaluation_details JSONB DEFAULT '{}',
    execution_time_ms INTEGER,
    memory_usage_kb INTEGER,
    test_cases_passed INTEGER DEFAULT 0,
    total_test_cases INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create new table for practice sessions
CREATE TABLE IF NOT EXISTS practice_sessions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    interview_type VARCHAR(100) NOT NULL,
    topic VARCHAR(100) NOT NULL,
    difficulty VARCHAR(20) DEFAULT 'intermediate',
    questions_attempted INTEGER DEFAULT 0,
    questions_correct INTEGER DEFAULT 0,
    total_score DECIMAL(5,2) DEFAULT 0.0,
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    end_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Update existing questions to have a default interview_type
UPDATE questions 
SET interview_type = 'Software Engineer' 
WHERE interview_type IS NULL;

-- Make interview_type NOT NULL after setting defaults
ALTER TABLE questions ALTER COLUMN interview_type SET NOT NULL;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_questions_interview_type ON questions(interview_type);
CREATE INDEX IF NOT EXISTS idx_security_events_session_id ON security_events(session_id);
CREATE INDEX IF NOT EXISTS idx_security_events_timestamp ON security_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_code_submissions_session_id ON code_submissions(session_id);
CREATE INDEX IF NOT EXISTS idx_code_submissions_language ON code_submissions(programming_language);
CREATE INDEX IF NOT EXISTS idx_practice_sessions_user_id ON practice_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_practice_sessions_topic ON practice_sessions(topic);

-- Add RLS policies for new tables
ALTER TABLE security_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE code_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE practice_sessions ENABLE ROW LEVEL SECURITY;

-- Security events policy
CREATE POLICY "Users can view own security events" ON security_events
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM sessions 
            WHERE sessions.id = security_events.session_id 
            AND sessions.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert own security events" ON security_events
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM sessions 
            WHERE sessions.id = security_events.session_id 
            AND sessions.user_id = auth.uid()
        )
    );

-- Code submissions policy
CREATE POLICY "Users can view own code submissions" ON code_submissions
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM sessions 
            WHERE sessions.id = code_submissions.session_id 
            AND sessions.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert own code submissions" ON code_submissions
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM sessions 
            WHERE sessions.id = code_submissions.session_id 
            AND sessions.user_id = auth.uid()
        )
    );

-- Practice sessions policy
CREATE POLICY "Users can view own practice sessions" ON practice_sessions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own practice sessions" ON practice_sessions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own practice sessions" ON practice_sessions
    FOR UPDATE USING (auth.uid() = user_id);

-- Verify the changes
SELECT 
    table_name, 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name IN ('questions', 'sessions', 'security_events', 'code_submissions', 'practice_sessions')
ORDER BY table_name, ordinal_position;
