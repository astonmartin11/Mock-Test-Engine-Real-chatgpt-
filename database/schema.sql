-- ============================================================
-- Adaptive AI Mock Test Engine & Personal Tutor
-- PostgreSQL / Neon Database Schema
-- Version: 1.0
--
-- Purpose:
--   Persistent student memory, adaptive testing, document/RAG
--   storage metadata, handwritten-answer evaluation, tutor
--   memory, AI usage tracking, and prompt/model versioning.
--
-- Notes:
--   1) Large files are stored in Cloudflare R2, NOT PostgreSQL.
--   2) This schema assumes PostgreSQL (Neon).
--   3) pgvector is enabled for document embeddings.
--   4) The application should connect with a backend DB role.
-- ============================================================


-- ============================================================
-- 0. EXTENSIONS
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;


-- ============================================================
-- 1. HELPER: AUTOMATIC updated_at
-- ============================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


-- ============================================================
-- 2. USERS
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    auth_provider TEXT NOT NULL DEFAULT 'google',
    auth_subject TEXT NOT NULL,

    email TEXT,
    display_name TEXT,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,

    -- Application-level quotas. These are NOT provider quotas.
    daily_ai_limit INTEGER NOT NULL DEFAULT 50,
    daily_test_limit INTEGER NOT NULL DEFAULT 3,
    daily_evaluation_limit INTEGER NOT NULL DEFAULT 10,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (auth_provider, auth_subject),

    CHECK (daily_ai_limit >= 0),
    CHECK (daily_test_limit >= 0),
    CHECK (daily_evaluation_limit >= 0)
);


CREATE INDEX IF NOT EXISTS idx_users_email
ON users(email);


CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();


-- ============================================================
-- 3. USER PREFERENCES
-- ============================================================

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id UUID PRIMARY KEY
        REFERENCES users(id)
        ON DELETE CASCADE,

    default_difficulty INTEGER NOT NULL DEFAULT 3,
    preferred_language TEXT NOT NULL DEFAULT 'English',

    show_detailed_solutions BOOLEAN NOT NULL DEFAULT TRUE,
    tutor_style TEXT NOT NULL DEFAULT 'academic',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (default_difficulty BETWEEN 1 AND 5)
);


CREATE TRIGGER trg_user_preferences_updated_at
BEFORE UPDATE ON user_preferences
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();


-- ============================================================
-- 4. SUBJECTS
-- ============================================================

CREATE TABLE IF NOT EXISTS subjects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,

    name TEXT NOT NULL,
    code TEXT,
    description TEXT,

    active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (user_id, name)
);


CREATE INDEX IF NOT EXISTS idx_subjects_user
ON subjects(user_id);


CREATE TRIGGER trg_subjects_updated_at
BEFORE UPDATE ON subjects
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();


-- ============================================================
-- 5. TOPICS
-- ============================================================

CREATE TABLE IF NOT EXISTS topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    subject_id UUID NOT NULL
        REFERENCES subjects(id)
        ON DELETE CASCADE,

    parent_topic_id UUID
        REFERENCES topics(id)
        ON DELETE SET NULL,

    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    description TEXT,

    syllabus_weight NUMERIC(6,4) NOT NULL DEFAULT 1.0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (subject_id, normalized_name),

    CHECK (syllabus_weight >= 0)
);


CREATE INDEX IF NOT EXISTS idx_topics_subject
ON topics(subject_id);


CREATE INDEX IF NOT EXISTS idx_topics_parent
ON topics(parent_topic_id);


-- ============================================================
-- 6. TOPIC MASTERY / GREY AREAS
-- ============================================================

CREATE TABLE IF NOT EXISTS topic_mastery (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,

    topic_id UUID NOT NULL
        REFERENCES topics(id)
        ON DELETE CASCADE,

    -- All normalized mastery values are 0..1.
    mastery_score NUMERIC(6,4) NOT NULL DEFAULT 0.5000,
    raw_ema_score NUMERIC(6,4) NOT NULL DEFAULT 0.5000,
    confidence NUMERIC(6,4) NOT NULL DEFAULT 0.0000,

    attempt_count INTEGER NOT NULL DEFAULT 0,
    low_score_streak INTEGER NOT NULL DEFAULT 0,

    recent_score NUMERIC(6,4),
    highest_score NUMERIC(6,4),

    is_grey_area BOOLEAN NOT NULL DEFAULT FALSE,

    last_attempt_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (user_id, topic_id),

    CHECK (mastery_score BETWEEN 0 AND 1),
    CHECK (raw_ema_score BETWEEN 0 AND 1),
    CHECK (confidence BETWEEN 0 AND 1),
    CHECK (attempt_count >= 0),
    CHECK (low_score_streak >= 0),
    CHECK (recent_score IS NULL OR recent_score BETWEEN 0 AND 1),
    CHECK (highest_score IS NULL OR highest_score BETWEEN 0 AND 1)
);


CREATE INDEX IF NOT EXISTS idx_topic_mastery_user_grey
ON topic_mastery(user_id, is_grey_area, mastery_score);


CREATE INDEX IF NOT EXISTS idx_topic_mastery_topic
ON topic_mastery(topic_id);


CREATE TRIGGER trg_topic_mastery_updated_at
BEFORE UPDATE ON topic_mastery
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();


-- ============================================================
-- 7. DOCUMENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,

    subject_id UUID NOT NULL
        REFERENCES subjects(id)
        ON DELETE CASCADE,

    document_type TEXT NOT NULL,
    -- syllabus / notes / slides / pyq / reference / answer_sheet

    filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,

    storage_provider TEXT NOT NULL DEFAULT 'r2',
    storage_key TEXT NOT NULL,

    file_size_bytes BIGINT,
    sha256 TEXT NOT NULL,

    page_count INTEGER,

    processing_status TEXT NOT NULL DEFAULT 'queued',
    -- queued / processing / completed / failed

    extracted_text_available BOOLEAN NOT NULL DEFAULT FALSE,
    vision_processed BOOLEAN NOT NULL DEFAULT FALSE,
    embedding_processed BOOLEAN NOT NULL DEFAULT FALSE,

    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ,

    UNIQUE (subject_id, sha256),

    CHECK (file_size_bytes IS NULL OR file_size_bytes >= 0),
    CHECK (page_count IS NULL OR page_count >= 0),
    CHECK (
        document_type IN (
            'syllabus',
            'notes',
            'slides',
            'pyq',
            'reference',
            'answer_sheet'
        )
    ),
    CHECK (
        processing_status IN (
            'queued',
            'processing',
            'completed',
            'failed'
        )
    )
);


CREATE INDEX IF NOT EXISTS idx_documents_subject
ON documents(subject_id);


CREATE INDEX IF NOT EXISTS idx_documents_user
ON documents(user_id);


CREATE INDEX IF NOT EXISTS idx_documents_status
ON documents(processing_status);


-- ============================================================
-- 8. DOCUMENT PAGES
-- ============================================================

CREATE TABLE IF NOT EXISTS document_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    document_id UUID NOT NULL
        REFERENCES documents(id)
        ON DELETE CASCADE,

    page_number INTEGER NOT NULL,

    extracted_text TEXT,

    text_length INTEGER,

    has_images BOOLEAN NOT NULL DEFAULT FALSE,
    has_tables BOOLEAN NOT NULL DEFAULT FALSE,
    has_formulas BOOLEAN NOT NULL DEFAULT FALSE,

    needs_vision BOOLEAN NOT NULL DEFAULT FALSE,

    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    UNIQUE (document_id, page_number),

    CHECK (page_number > 0),
    CHECK (text_length IS NULL OR text_length >= 0)
);


CREATE INDEX IF NOT EXISTS idx_document_pages_document
ON document_pages(document_id, page_number);


-- ============================================================
-- 9. DOCUMENT CHUNKS / RAG
-- ============================================================

CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    document_id UUID NOT NULL
        REFERENCES documents(id)
        ON DELETE CASCADE,

    page_id UUID
        REFERENCES document_pages(id)
        ON DELETE SET NULL,

    topic_id UUID
        REFERENCES topics(id)
        ON DELETE SET NULL,

    chunk_index INTEGER NOT NULL,

    title TEXT,
    content TEXT NOT NULL,

    chunk_type TEXT NOT NULL DEFAULT 'text',
    -- text / formula / derivation / table / figure / example / pyq

    token_count INTEGER,

    -- BGE-small-en-v1.5 = 384 dimensions.
    -- If a different embedding model is selected later, migrate
    -- this column/index accordingly.
    embedding vector(384),

    -- Maintained by trigger for lexical retrieval.
    search_vector TSVECTOR,

    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (document_id, chunk_index),

    CHECK (chunk_index >= 0),
    CHECK (
        chunk_type IN (
            'text',
            'formula',
            'derivation',
            'table',
            'figure',
            'example',
            'pyq'
        )
    ),
    CHECK (token_count IS NULL OR token_count >= 0)
);


CREATE INDEX IF NOT EXISTS idx_document_chunks_document
ON document_chunks(document_id, chunk_index);


CREATE INDEX IF NOT EXISTS idx_document_chunks_topic
ON document_chunks(topic_id);


CREATE INDEX IF NOT EXISTS idx_document_chunks_search
ON document_chunks
USING GIN(search_vector);


-- Optional vector index. For small datasets, exact cosine search
-- can be cheaper/simpler. Enable HNSW once the corpus is large.
--
-- CREATE INDEX idx_document_chunks_embedding
-- ON document_chunks
-- USING hnsw (embedding vector_cosine_ops);


CREATE OR REPLACE FUNCTION update_document_chunk_search_vector()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.search_vector :=
        to_tsvector(
            'english',
            COALESCE(NEW.title, '') || ' ' || COALESCE(NEW.content, '')
        );
    RETURN NEW;
END;
$$;


DROP TRIGGER IF EXISTS trg_document_chunk_search_vector
ON document_chunks;


CREATE TRIGGER trg_document_chunk_search_vector
BEFORE INSERT OR UPDATE OF title, content
ON document_chunks
FOR EACH ROW
EXECUTE FUNCTION update_document_chunk_search_vector();


-- ============================================================
-- 10. TESTS
-- ============================================================

CREATE TABLE IF NOT EXISTS tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,

    subject_id UUID NOT NULL
        REFERENCES subjects(id)
        ON DELETE CASCADE,

    title TEXT NOT NULL,

    difficulty INTEGER NOT NULL DEFAULT 3,

    num_numericals INTEGER NOT NULL DEFAULT 0,
    num_derivations INTEGER NOT NULL DEFAULT 0,
    num_theory INTEGER NOT NULL DEFAULT 0,

    duration_minutes INTEGER,

    critical_override TEXT,

    grey_area_snapshot JSONB NOT NULL DEFAULT '[]'::jsonb,

    generation_status TEXT NOT NULL DEFAULT 'processing',

    total_marks NUMERIC(8,2),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (difficulty BETWEEN 1 AND 5),
    CHECK (num_numericals >= 0),
    CHECK (num_derivations >= 0),
    CHECK (num_theory >= 0),
    CHECK (duration_minutes IS NULL OR duration_minutes > 0),
    CHECK (
        generation_status IN (
            'processing',
            'completed',
            'failed'
        )
    ),
    CHECK (total_marks IS NULL OR total_marks >= 0)
);


CREATE INDEX IF NOT EXISTS idx_tests_user_subject
ON tests(user_id, subject_id, created_at DESC);


-- ============================================================
-- 11. QUESTIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    subject_id UUID NOT NULL
        REFERENCES subjects(id)
        ON DELETE CASCADE,

    question_type TEXT NOT NULL,
    -- numerical / derivation / theory

    difficulty INTEGER NOT NULL,

    question_text TEXT NOT NULL,

    -- SERVER-SIDE ONLY.
    -- Never send this to the student-facing PDF.
    solution_json JSONB NOT NULL,

    -- SERVER-SIDE grading structure.
    grading_rubric JSONB NOT NULL,

    expected_answer TEXT,

    marks NUMERIC(8,2) NOT NULL,

    generation_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (
        question_type IN (
            'numerical',
            'derivation',
            'theory'
        )
    ),
    CHECK (difficulty BETWEEN 1 AND 5),
    CHECK (marks > 0)
);


CREATE INDEX IF NOT EXISTS idx_questions_subject
ON questions(subject_id);


CREATE INDEX IF NOT EXISTS idx_questions_type_difficulty
ON questions(subject_id, question_type, difficulty);


-- ============================================================
-- 12. QUESTION TOPICS
-- ============================================================

CREATE TABLE IF NOT EXISTS question_topics (
    question_id UUID NOT NULL
        REFERENCES questions(id)
        ON DELETE CASCADE,

    topic_id UUID NOT NULL
        REFERENCES topics(id)
        ON DELETE CASCADE,

    relevance_weight NUMERIC(6,4) NOT NULL DEFAULT 1.0,

    is_primary BOOLEAN NOT NULL DEFAULT FALSE,

    PRIMARY KEY (question_id, topic_id),

    CHECK (relevance_weight >= 0)
);


CREATE INDEX IF NOT EXISTS idx_question_topics_topic
ON question_topics(topic_id);


-- ============================================================
-- 13. QUESTION EVIDENCE
-- ============================================================

CREATE TABLE IF NOT EXISTS question_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    question_id UUID NOT NULL
        REFERENCES questions(id)
        ON DELETE CASCADE,

    chunk_id UUID NOT NULL
        REFERENCES document_chunks(id)
        ON DELETE CASCADE,

    relevance_score NUMERIC(6,4),

    supporting_excerpt TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(question_id, chunk_id),

    CHECK (
        relevance_score IS NULL
        OR relevance_score BETWEEN 0 AND 1
    )
);


CREATE INDEX IF NOT EXISTS idx_question_evidence_question
ON question_evidence(question_id);


CREATE INDEX IF NOT EXISTS idx_question_evidence_chunk
ON question_evidence(chunk_id);


-- ============================================================
-- 14. TEST QUESTIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS test_questions (
    test_id UUID NOT NULL
        REFERENCES tests(id)
        ON DELETE CASCADE,

    question_id UUID NOT NULL
        REFERENCES questions(id)
        ON DELETE RESTRICT,

    question_number INTEGER NOT NULL,

    marks_override NUMERIC(8,2),

    PRIMARY KEY (test_id, question_id),

    UNIQUE (test_id, question_number),

    CHECK (question_number > 0),
    CHECK (marks_override IS NULL OR marks_override > 0)
);


-- ============================================================
-- 15. ATTEMPTS
-- ============================================================

CREATE TABLE IF NOT EXISTS attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,

    test_id UUID NOT NULL
        REFERENCES tests(id)
        ON DELETE CASCADE,

    started_at TIMESTAMPTZ,
    submitted_at TIMESTAMPTZ,

    status TEXT NOT NULL DEFAULT 'in_progress',
    -- in_progress / submitted / evaluating / evaluated / failed

    total_score NUMERIC(8,2),
    total_marks NUMERIC(8,2),

    percentage NUMERIC(6,3),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (
        status IN (
            'in_progress',
            'submitted',
            'evaluating',
            'evaluated',
            'failed'
        )
    ),
    CHECK (total_score IS NULL OR total_score >= 0),
    CHECK (total_marks IS NULL OR total_marks >= 0),
    CHECK (
        percentage IS NULL
        OR percentage BETWEEN 0 AND 100
    )
);


CREATE INDEX IF NOT EXISTS idx_attempts_user
ON attempts(user_id, created_at DESC);


CREATE INDEX IF NOT EXISTS idx_attempts_test
ON attempts(test_id);


-- ============================================================
-- 16. ATTEMPT ANSWERS
-- ============================================================

CREATE TABLE IF NOT EXISTS attempt_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    attempt_id UUID NOT NULL
        REFERENCES attempts(id)
        ON DELETE CASCADE,

    question_id UUID NOT NULL
        REFERENCES questions(id)
        ON DELETE RESTRICT,

    answer_mode TEXT NOT NULL,
    -- text / image / pdf

    raw_text TEXT,

    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    status TEXT NOT NULL DEFAULT 'submitted',

    UNIQUE (attempt_id, question_id),

    CHECK (
        answer_mode IN (
            'text',
            'image',
            'pdf'
        )
    ),
    CHECK (
        status IN (
            'submitted',
            'transcribing',
            'transcribed',
            'evaluating',
            'evaluated',
            'failed'
        )
    )
);


CREATE INDEX IF NOT EXISTS idx_attempt_answers_attempt
ON attempt_answers(attempt_id);


-- ============================================================
-- 17. ANSWER ARTIFACTS
-- ============================================================

CREATE TABLE IF NOT EXISTS answer_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    attempt_answer_id UUID NOT NULL
        REFERENCES attempt_answers(id)
        ON DELETE CASCADE,

    storage_key TEXT NOT NULL,

    mime_type TEXT NOT NULL,
    file_size_bytes BIGINT,

    sha256 TEXT,

    page_count INTEGER,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (file_size_bytes IS NULL OR file_size_bytes >= 0),
    CHECK (page_count IS NULL OR page_count >= 0)
);


CREATE INDEX IF NOT EXISTS idx_answer_artifacts_answer
ON answer_artifacts(attempt_answer_id);


-- ============================================================
-- 18. TRANSCRIPTIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS transcriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    attempt_answer_id UUID NOT NULL
        REFERENCES attempt_answers(id)
        ON DELETE CASCADE,

    provider TEXT NOT NULL,
    model TEXT NOT NULL,

    transcript_text TEXT NOT NULL,

    latex_text TEXT,

    confidence NUMERIC(6,4),

    structured_content JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (
        confidence IS NULL
        OR confidence BETWEEN 0 AND 1
    )
);


CREATE INDEX IF NOT EXISTS idx_transcriptions_answer
ON transcriptions(attempt_answer_id, created_at DESC);


-- ============================================================
-- 19. EVALUATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    attempt_answer_id UUID NOT NULL
        REFERENCES attempt_answers(id)
        ON DELETE CASCADE,

    provider TEXT NOT NULL,
    model TEXT NOT NULL,

    score NUMERIC(8,3) NOT NULL,
    max_score NUMERIC(8,3) NOT NULL,

    correctness NUMERIC(6,4),

    feedback TEXT NOT NULL,

    final_verdict TEXT,

    is_grey_area BOOLEAN NOT NULL DEFAULT FALSE,

    needs_manual_review BOOLEAN NOT NULL DEFAULT FALSE,

    evaluation_json JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (score >= 0),
    CHECK (max_score > 0),
    CHECK (score <= max_score),
    CHECK (
        correctness IS NULL
        OR correctness BETWEEN 0 AND 1
    )
);


CREATE INDEX IF NOT EXISTS idx_evaluations_answer
ON evaluations(attempt_answer_id, created_at DESC);


-- ============================================================
-- 20. EVALUATION STEPS
-- ============================================================

CREATE TABLE IF NOT EXISTS evaluation_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    evaluation_id UUID NOT NULL
        REFERENCES evaluations(id)
        ON DELETE CASCADE,

    step_number INTEGER NOT NULL,

    student_step TEXT,
    expected_step TEXT,

    step_score NUMERIC(8,3),
    step_max_score NUMERIC(8,3),

    status TEXT NOT NULL,
    -- correct / partially_correct / incorrect / missing

    error_type TEXT,
    -- algebra / sign / formula / concept / unit /
    -- arithmetic / assumption / interpretation / notation / other

    feedback TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (evaluation_id, step_number),

    CHECK (step_number > 0),
    CHECK (
        step_score IS NULL
        OR step_score >= 0
    ),
    CHECK (
        step_max_score IS NULL
        OR step_max_score > 0
    ),
    CHECK (
        status IN (
            'correct',
            'partially_correct',
            'incorrect',
            'missing'
        )
    ),
    CHECK (
        error_type IS NULL
        OR error_type IN (
            'algebra',
            'sign',
            'formula',
            'concept',
            'unit',
            'arithmetic',
            'assumption',
            'interpretation',
            'notation',
            'other'
        )
    )
);


CREATE INDEX IF NOT EXISTS idx_evaluation_steps_evaluation
ON evaluation_steps(evaluation_id, step_number);


-- ============================================================
-- 21. EVALUATION TOPIC RESULTS
-- ============================================================

CREATE TABLE IF NOT EXISTS evaluation_topic_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    evaluation_id UUID NOT NULL
        REFERENCES evaluations(id)
        ON DELETE CASCADE,

    topic_id UUID NOT NULL
        REFERENCES topics(id)
        ON DELETE CASCADE,

    score NUMERIC(8,3),
    max_score NUMERIC(8,3),

    normalized_score NUMERIC(6,4),

    error_severity NUMERIC(6,4) DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (evaluation_id, topic_id),

    CHECK (
        normalized_score IS NULL
        OR normalized_score BETWEEN 0 AND 1
    ),
    CHECK (
        error_severity IS NULL
        OR error_severity BETWEEN 0 AND 1
    )
);


CREATE INDEX IF NOT EXISTS idx_evaluation_topic_results_topic
ON evaluation_topic_results(topic_id);


-- ============================================================
-- 22. TUTOR CONVERSATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS tutor_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,

    subject_id UUID NOT NULL
        REFERENCES subjects(id)
        ON DELETE CASCADE,

    title TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE INDEX IF NOT EXISTS idx_tutor_conversations_user_subject
ON tutor_conversations(user_id, subject_id, updated_at DESC);


CREATE TRIGGER trg_tutor_conversations_updated_at
BEFORE UPDATE ON tutor_conversations
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();


-- ============================================================
-- 23. TUTOR MESSAGES
-- ============================================================

CREATE TABLE IF NOT EXISTS tutor_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    conversation_id UUID NOT NULL
        REFERENCES tutor_conversations(id)
        ON DELETE CASCADE,

    role TEXT NOT NULL,
    -- user / assistant / system

    content TEXT NOT NULL,

    model TEXT,

    token_estimate INTEGER,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (role IN ('user', 'assistant', 'system')),
    CHECK (token_estimate IS NULL OR token_estimate >= 0)
);


CREATE INDEX IF NOT EXISTS idx_tutor_messages_conversation
ON tutor_messages(conversation_id, created_at);


-- ============================================================
-- 24. TUTOR MEMORY
-- ============================================================

CREATE TABLE IF NOT EXISTS tutor_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,

    subject_id UUID NOT NULL
        REFERENCES subjects(id)
        ON DELETE CASCADE,

    memory_type TEXT NOT NULL,
    -- misconception / preference / goal /
    -- recurring_error / strength

    topic_id UUID
        REFERENCES topics(id)
        ON DELETE SET NULL,

    memory_text TEXT NOT NULL,

    confidence NUMERIC(6,4) NOT NULL DEFAULT 0.5,

    source_message_id UUID
        REFERENCES tutor_messages(id)
        ON DELETE SET NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (confidence BETWEEN 0 AND 1)
);


CREATE INDEX IF NOT EXISTS idx_tutor_memory_user_subject
ON tutor_memory(user_id, subject_id);


CREATE INDEX IF NOT EXISTS idx_tutor_memory_topic
ON tutor_memory(topic_id);


CREATE TRIGGER trg_tutor_memory_updated_at
BEFORE UPDATE ON tutor_memory
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();


-- ============================================================
-- 25. PROCESSING JOBS
-- ============================================================

CREATE TABLE IF NOT EXISTS processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID
        REFERENCES users(id)
        ON DELETE CASCADE,

    subject_id UUID
        REFERENCES subjects(id)
        ON DELETE CASCADE,

    job_type TEXT NOT NULL,

    entity_id UUID,

    status TEXT NOT NULL DEFAULT 'queued',
    -- queued / processing / completed / failed

    progress INTEGER NOT NULL DEFAULT 0,

    current_step TEXT,

    attempts INTEGER NOT NULL DEFAULT 0,

    error_message TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    CHECK (progress BETWEEN 0 AND 100),
    CHECK (attempts >= 0),
    CHECK (
        status IN (
            'queued',
            'processing',
            'completed',
            'failed'
        )
    )
);


CREATE INDEX IF NOT EXISTS idx_processing_jobs_status
ON processing_jobs(status, created_at);


CREATE INDEX IF NOT EXISTS idx_processing_jobs_user
ON processing_jobs(user_id, created_at DESC);


-- ============================================================
-- 26. AI RUNS / OBSERVABILITY
-- ============================================================

CREATE TABLE IF NOT EXISTS ai_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID
        REFERENCES users(id)
        ON DELETE SET NULL,

    subject_id UUID
        REFERENCES subjects(id)
        ON DELETE SET NULL,

    task_type TEXT NOT NULL,

    provider TEXT NOT NULL,
    model TEXT NOT NULL,

    prompt_version TEXT,

    input_tokens INTEGER,
    output_tokens INTEGER,

    estimated_cost NUMERIC(12,6),

    status TEXT NOT NULL,
    -- success / error / rate_limited / timeout

    latency_ms INTEGER,

    cache_hit BOOLEAN NOT NULL DEFAULT FALSE,

    request_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (input_tokens IS NULL OR input_tokens >= 0),
    CHECK (output_tokens IS NULL OR output_tokens >= 0),
    CHECK (estimated_cost IS NULL OR estimated_cost >= 0),
    CHECK (latency_ms IS NULL OR latency_ms >= 0),
    CHECK (
        status IN (
            'success',
            'error',
            'rate_limited',
            'timeout'
        )
    )
);


CREATE INDEX IF NOT EXISTS idx_ai_runs_user_date
ON ai_runs(user_id, created_at DESC);


CREATE INDEX IF NOT EXISTS idx_ai_runs_task
ON ai_runs(task_type, created_at DESC);


-- ============================================================
-- 27. API USAGE
-- ============================================================

CREATE TABLE IF NOT EXISTS api_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,

    provider TEXT NOT NULL,
    model TEXT NOT NULL,

    operation TEXT NOT NULL,

    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,

    request_count INTEGER NOT NULL DEFAULT 1,

    usage_date DATE NOT NULL DEFAULT CURRENT_DATE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (input_tokens >= 0),
    CHECK (output_tokens >= 0),
    CHECK (request_count > 0)
);


CREATE INDEX IF NOT EXISTS idx_api_usage_daily
ON api_usage(user_id, usage_date);


CREATE INDEX IF NOT EXISTS idx_api_usage_provider_day
ON api_usage(provider, model, usage_date);


-- ============================================================
-- 28. PROMPT VERSIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS prompt_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    prompt_name TEXT NOT NULL,
    version TEXT NOT NULL,

    system_prompt TEXT NOT NULL,

    output_schema JSONB,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (prompt_name, version)
);


CREATE INDEX IF NOT EXISTS idx_prompt_versions_active
ON prompt_versions(prompt_name, is_active);


-- ============================================================
-- 29. AI CACHE
-- ============================================================

CREATE TABLE IF NOT EXISTS ai_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    request_hash TEXT NOT NULL UNIQUE,

    task_type TEXT NOT NULL,

    provider TEXT NOT NULL,
    model TEXT NOT NULL,

    response_json JSONB NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);


CREATE INDEX IF NOT EXISTS idx_ai_cache_expiration
ON ai_cache(expires_at);


-- ============================================================
-- 30. OPTIONAL: SYSTEM MODEL CONFIGURATION
-- ============================================================
-- Centralized model configuration prevents provider model names
-- from being scattered through Python code.

CREATE TABLE IF NOT EXISTS model_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    task_type TEXT NOT NULL,

    provider TEXT NOT NULL,
    model_name TEXT NOT NULL,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    priority INTEGER NOT NULL DEFAULT 1,

    max_input_tokens INTEGER,
    max_output_tokens INTEGER,

    configuration JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(task_type, provider, model_name),

    CHECK (priority > 0),
    CHECK (
        max_input_tokens IS NULL
        OR max_input_tokens > 0
    ),
    CHECK (
        max_output_tokens IS NULL
        OR max_output_tokens > 0
    )
);


CREATE INDEX IF NOT EXISTS idx_model_registry_task
ON model_registry(task_type, is_active, priority);


-- ============================================================
-- 31. SEED INITIAL MODEL ROUTING
-- ============================================================
-- These are configuration records, not hard-coded application
-- logic. Change them later without changing the DB schema.

INSERT INTO model_registry
    (task_type, provider, model_name, is_active, priority)
VALUES
    ('DOCUMENT_VISION', 'google', 'gemini-3.8-flash', TRUE, 1),
    ('DOCUMENT_SUMMARIZE', 'google', 'gemini-3.8-flash', TRUE, 1),
    ('TOPIC_EXTRACTION', 'google', 'gemini-3.8-flash', TRUE, 1),
    ('QUESTION_DRAFT', 'google', 'gemini-3.8-flash', TRUE, 1),
    ('ANSWER_TRANSCRIBE', 'google', 'gemini-3.8-flash', TRUE, 1),
    ('TUTOR_SIMPLE', 'google', 'gemini-3.8-flash', TRUE, 1),
    ('QUESTION_VALIDATE', 'groq', 'openai/gpt-oss-120b', TRUE, 1),
    ('SOLUTION_GENERATE', 'groq', 'openai/gpt-oss-120b', TRUE, 1),
    ('ANSWER_GRADE', 'groq', 'openai/gpt-oss-120b', TRUE, 1),
    ('TUTOR_ADVANCED', 'groq', 'openai/gpt-oss-120b', TRUE, 1)
ON CONFLICT (task_type, provider, model_name)
DO NOTHING;


-- ============================================================
-- 32. DATABASE SANITY VIEW: CURRENT GREY AREAS
-- ============================================================

CREATE OR REPLACE VIEW current_grey_areas AS
SELECT
    tm.user_id,
    t.subject_id,
    tm.topic_id,
    t.name AS topic_name,
    tm.mastery_score,
    tm.confidence,
    tm.attempt_count,
    tm.low_score_streak,
    tm.last_attempt_at
FROM topic_mastery tm
JOIN topics t
    ON t.id = tm.topic_id
WHERE tm.is_grey_area = TRUE;


-- ============================================================
-- 33. DATABASE SANITY VIEW: RECENT STUDENT PERFORMANCE
-- ============================================================

CREATE OR REPLACE VIEW recent_attempt_performance AS
SELECT
    a.user_id,
    a.test_id,
    a.id AS attempt_id,
    a.total_score,
    a.total_marks,
    a.percentage,
    a.status,
    a.created_at
FROM attempts a
WHERE a.status = 'evaluated'
ORDER BY a.created_at DESC;


-- ============================================================
-- 34. VERIFICATION QUERIES
-- ============================================================
-- Run these after executing this file:
--
-- SELECT extname FROM pg_extension
-- WHERE extname IN ('pgcrypto', 'vector')
-- ORDER BY extname;
--
-- SELECT table_name
-- FROM information_schema.tables
-- WHERE table_schema = 'public'
-- ORDER BY table_name;
--
-- SELECT * FROM model_registry
-- ORDER BY task_type, priority;
--
-- SELECT * FROM current_grey_areas;
--
-- ============================================================
-- END OF SCHEMA
-- ============================================================
