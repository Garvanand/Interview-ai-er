-- 002_question_embeddings.sql
-- Vector storage schema for question embeddings using MiniLM.
-- Stores dense 384-dimensional embeddings in PostgreSQL/Supabase without requiring an external vector DB.

CREATE TABLE IF NOT EXISTS question_embeddings (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    question_id VARCHAR(100) NOT NULL UNIQUE,
    embedding_model VARCHAR(100) NOT NULL DEFAULT 'sentence-transformers/all-MiniLM-L6-v2',
    embedding_version VARCHAR(50) NOT NULL DEFAULT 'all-minilm-l6-v2',
    embedding_vector JSONB NOT NULL, -- 384-dimensional float array
    question_text TEXT,
    skill_focus VARCHAR(100),
    difficulty VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE question_embeddings ENABLE ROW LEVEL SECURITY;

-- Allow read access to authenticated and service role users
CREATE POLICY "Allow read access to question_embeddings"
    ON question_embeddings FOR SELECT
    USING (true);

-- Allow write access to service role users
CREATE POLICY "Allow service role write access to question_embeddings"
    ON question_embeddings FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role' OR auth.role() = 'authenticated');

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_question_embeddings_question_id ON question_embeddings(question_id);
CREATE INDEX IF NOT EXISTS idx_question_embeddings_skill_focus ON question_embeddings(skill_focus);
CREATE INDEX IF NOT EXISTS idx_question_embeddings_difficulty ON question_embeddings(difficulty);
CREATE INDEX IF NOT EXISTS idx_question_embeddings_model_version ON question_embeddings(embedding_model, embedding_version);
