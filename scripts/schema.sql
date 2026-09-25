-- =========================================================================
-- Kenyan RAG Chatbot — Database Schema
-- SQLite compatible
-- =========================================================================

-- 1. USERS ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username        VARCHAR(50) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('citizen','evaluator','admin')),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login      TIMESTAMP,
    is_active       BOOLEAN DEFAULT 1
);

-- 2. DOCUMENTS -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    document_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title           VARCHAR(255) NOT NULL,
    party           VARCHAR(100),
    year            INTEGER,
    source_type     VARCHAR(50),
    file_path       VARCHAR(500),
    content_length  INTEGER,
    ingested_by     INTEGER,
    ingested_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active       BOOLEAN DEFAULT 1,
    FOREIGN KEY (ingested_by) REFERENCES users(user_id) ON DELETE SET NULL
);

-- 3. CHUNKS --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id     INTEGER NOT NULL,
    chunk_index     INTEGER,
    chunk_text      TEXT NOT NULL,
    char_start      INTEGER,
    char_end        INTEGER,
    is_promise      BOOLEAN DEFAULT 0,
    promise_score   REAL DEFAULT 0.0,
    matched_keywords TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
);

-- 4. QUERIES -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS queries (
    query_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    query_text      TEXT NOT NULL,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    was_answered    BOOLEAN DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 5. RESPONSES -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS responses (
    response_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id        INTEGER NOT NULL UNIQUE,
    response_text   TEXT NOT NULL,
    prompt_used     TEXT,
    tokens_prompt   INTEGER,
    tokens_response INTEGER,
    model_version   VARCHAR(50),
    retrieval_ms    INTEGER,
    generation_ms   INTEGER,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (query_id) REFERENCES queries(query_id) ON DELETE CASCADE
);

-- 6. CITATIONS -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS citations (
    citation_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    response_id     INTEGER NOT NULL,
    chunk_id        INTEGER NOT NULL,
    citation_order  INTEGER,
    similarity      REAL,
    FOREIGN KEY (response_id) REFERENCES responses(response_id) ON DELETE CASCADE,
    FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id) ON DELETE CASCADE
);

-- 7. FEEDBACK ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS feedback (
    feedback_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    response_id     INTEGER NOT NULL,
    user_id         INTEGER NOT NULL,
    feedback_type   VARCHAR(10) CHECK (feedback_type IN ('positive','negative')),
    comment         TEXT,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (response_id) REFERENCES responses(response_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 8. EVALUATIONS ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS evaluations (
    eval_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    evaluator_id    INTEGER NOT NULL,
    test_query      TEXT NOT NULL,
    precision_at_5  REAL,
    bm25_precision  REAL,
    faithfulness    REAL,
    run_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evaluator_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 9. HUMAN REVIEWS -------------------------------------------------------
CREATE TABLE IF NOT EXISTS human_reviews (
    review_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    eval_id         INTEGER,
    reviewer_id     INTEGER NOT NULL,
    query_text      TEXT NOT NULL,
    answer_text     TEXT,
    accuracy_score  INTEGER CHECK (accuracy_score BETWEEN 1 AND 5),
    relevance_score INTEGER CHECK (relevance_score BETWEEN 1 AND 5),
    citation_score  INTEGER CHECK (citation_score BETWEEN 1 AND 5),
    comments        TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (eval_id) REFERENCES evaluations(eval_id) ON DELETE SET NULL,
    FOREIGN KEY (reviewer_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 10. INGESTION LOGS -----------------------------------------------------
CREATE TABLE IF NOT EXISTS ingestion_logs (
    log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id     INTEGER,
    ingested_by     INTEGER,
    total_chunks    INTEGER,
    promise_chunks  INTEGER,
    duration_sec    INTEGER,
    status          VARCHAR(20),
    error_message   TEXT,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE SET NULL,
    FOREIGN KEY (ingested_by) REFERENCES users(user_id) ON DELETE SET NULL
);

-- 11. SYSTEM CONFIG ------------------------------------------------------
CREATE TABLE IF NOT EXISTS system_config (
    config_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key      VARCHAR(50) UNIQUE NOT NULL,
    config_value    TEXT,
    description     TEXT,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================================
-- Indexes for performance
-- =========================================================================
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_documents_party ON documents(party);
CREATE INDEX IF NOT EXISTS idx_documents_year ON documents(year);
CREATE INDEX IF NOT EXISTS idx_chunks_promise ON chunks(is_promise);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_queries_user ON queries(user_id);
CREATE INDEX IF NOT EXISTS idx_queries_time ON queries(timestamp);
CREATE INDEX IF NOT EXISTS idx_citations_response ON citations(response_id);
CREATE INDEX IF NOT EXISTS idx_evals_evaluator ON evaluations(evaluator_id);

-- =========================================================================
-- Seed default configuration
-- =========================================================================
INSERT OR IGNORE INTO system_config (config_key, config_value, description) VALUES
    ('embedding_model',     'all-MiniLM-L6-v2', 'SBERT model name'),
    ('llm_model',           'llama3:8b',        'Ollama model name'),
    ('chunk_size',          '500',              'Chunk size in words'),
    ('chunk_overlap',       '50',               'Chunk overlap in words'),
    ('top_k',               '5',                'Number of chunks retrieved'),
    ('similarity_threshold','0.5',              'Minimum similarity to accept'),
    ('promise_threshold',   '0.3',              'Minimum promise score');