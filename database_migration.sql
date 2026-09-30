-- Database Migration Script for Enhanced Backend Features
-- Run this in your Supabase SQL editor to add missing columns and tables

-- 1. Add missing columns to questions table
ALTER TABLE questions 
ADD COLUMN IF NOT EXISTS interview_type VARCHAR(100),
ADD COLUMN IF NOT EXISTS evaluation_feedback TEXT,
ADD COLUMN IF NOT EXISTS evaluation_details JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS code_text TEXT,
ADD COLUMN IF NOT EXISTS programming_language VARCHAR(50),
ADD COLUMN IF NOT EXISTS code_evaluation_score DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS code_evaluation_details JSONB DEFAULT '{}';

-- 2. Add missing columns to sessions table
ALTER TABLE sessions 
ADD COLUMN IF NOT EXISTS security_score DECIMAL(5,2) DEFAULT 100.00,
ADD COLUMN IF NOT EXISTS security_events_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_security_check TIMESTAMP WITH TIME ZONE;

-- 3. Create security_events table for enhanced security monitoring
CREATE TABLE IF NOT EXISTS security_events (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    security_level VARCHAR(20) DEFAULT 'medium',
    confidence_score DECIMAL(5,2) DEFAULT 0.00,
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Create code_submissions table for detailed code tracking
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

-- 5. Create practice_sessions table for practice mode
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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Create indexes for new tables
CREATE INDEX IF NOT EXISTS idx_security_events_session_id ON security_events(session_id);
CREATE INDEX IF NOT EXISTS idx_security_events_timestamp ON security_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_security_events_event_type ON security_events(event_type);

CREATE INDEX IF NOT EXISTS idx_code_submissions_session_id ON code_submissions(session_id);
CREATE INDEX IF NOT EXISTS idx_code_submissions_question_id ON code_submissions(question_id);
CREATE INDEX IF NOT EXISTS idx_code_submissions_language ON code_submissions(programming_language);

CREATE INDEX IF NOT EXISTS idx_practice_sessions_user_id ON practice_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_practice_sessions_topic ON practice_sessions(topic);
CREATE INDEX IF NOT EXISTS idx_practice_sessions_difficulty ON practice_sessions(difficulty);

-- 7. Add triggers for new tables
CREATE TRIGGER update_code_submissions_updated_at BEFORE UPDATE ON code_submissions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 8. Enable RLS on new tables
ALTER TABLE security_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE code_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE practice_sessions ENABLE ROW LEVEL SECURITY;

-- 9. Create RLS policies for security_events
CREATE POLICY "Users can view own security events" ON security_events
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM sessions 
            WHERE sessions.id = security_events.session_id 
            AND sessions.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert security events for own sessions" ON security_events
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM sessions 
            WHERE sessions.id = security_events.session_id 
            AND sessions.user_id = auth.uid()
        )
    );

-- 10. Create RLS policies for code_submissions
CREATE POLICY "Users can view own code submissions" ON code_submissions
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM sessions 
            WHERE sessions.id = code_submissions.session_id 
            AND sessions.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert code submissions for own sessions" ON code_submissions
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM sessions 
            WHERE sessions.id = code_submissions.session_id 
            AND sessions.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update own code submissions" ON code_submissions
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM sessions 
            WHERE sessions.id = code_submissions.session_id 
            AND sessions.user_id = auth.uid()
        )
    );

-- 11. Create RLS policies for practice_sessions
CREATE POLICY "Users can view own practice sessions" ON practice_sessions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own practice sessions" ON practice_sessions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own practice sessions" ON practice_sessions
    FOR UPDATE USING (auth.uid() = user_id);

-- 12. Update existing questions table structure to match new requirements
-- Add any missing columns that might be needed
ALTER TABLE questions 
ADD COLUMN IF NOT EXISTS question_type VARCHAR(100) DEFAULT 'technical',
ADD COLUMN IF NOT EXISTS difficulty VARCHAR(20) DEFAULT 'medium',
ADD COLUMN IF NOT EXISTS category VARCHAR(100),
ADD COLUMN IF NOT EXISTS expected_format VARCHAR(100),
ADD COLUMN IF NOT EXISTS hints JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS learning_objectives JSONB DEFAULT '[]';

-- 13. Add comments to document the schema
COMMENT ON TABLE questions IS 'Stores interview questions with enhanced metadata and evaluation';
COMMENT ON TABLE sessions IS 'Stores interview sessions with security monitoring';
COMMENT ON TABLE security_events IS 'Tracks security-related events during interviews';
COMMENT ON TABLE code_submissions IS 'Stores and tracks code submissions with evaluation';
COMMENT ON TABLE practice_sessions IS 'Tracks practice mode sessions and progress';

-- 14. Create skill_profiles table for longitudinal candidate intelligence
CREATE TABLE IF NOT EXISTS skill_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
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

-- 15. Create recommendations table for personalized candidate next actions
CREATE TABLE IF NOT EXISTS recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    session_id UUID,
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

CREATE INDEX IF NOT EXISTS idx_recommendations_user_id ON recommendations(user_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_status ON recommendations(status);
CREATE INDEX IF NOT EXISTS idx_skill_profiles_user_id ON skill_profiles(user_id);

-- 16. Verify the migration
DO $$
BEGIN
    -- Check if all required columns exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'questions' AND column_name = 'interview_type'
    ) THEN
        RAISE EXCEPTION 'Migration failed: interview_type column not found in questions table';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'sessions' AND column_name = 'security_score'
    ) THEN
        RAISE EXCEPTION 'Migration failed: security_score column not found in sessions table';
    END IF;
    
    RAISE NOTICE 'Migration completed successfully!';
END $$;
