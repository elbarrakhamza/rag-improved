-- Extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- Table des clés API
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    key_hash VARCHAR(64) UNIQUE NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'public', -- 'admin', 'employee', 'public'
    user_id INTEGER,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used TIMESTAMP
);

-- Table des documents
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    content TEXT,
    metadata JSONB,
    embedding vector(1024),
    feedback_score FLOAT DEFAULT 0,  -- Score moyen de feedback
    feedback_count INTEGER DEFAULT 0, -- Nombre de feedbacks
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index pour la recherche vectorielle
CREATE INDEX hnsw_index ON documents USING hnsw (embedding vector_cosine_ops);

-- Table de feedback
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    chunk_id INTEGER,
    score INTEGER CHECK (score >= 1 AND score <= 5),
    comment TEXT,
    api_key_id INTEGER REFERENCES api_keys(id) ON DELETE SET NULL,
    user_ip TEXT,
    is_helpful BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Table des questions récurrentes (pour analyse)
CREATE TABLE IF NOT EXISTS question_patterns (
    id SERIAL PRIMARY KEY,
    question_hash VARCHAR(64) UNIQUE,
    question_text TEXT,
    frequency INTEGER DEFAULT 1,
    avg_feedback_score FLOAT DEFAULT 0,
    last_asked TIMESTAMP DEFAULT NOW()
);

-- Index pour les performances
CREATE INDEX idx_feedback_document_id ON feedback(document_id);
CREATE INDEX idx_feedback_created_at ON feedback(created_at);
CREATE INDEX idx_api_keys_role ON api_keys(role);
CREATE INDEX idx_api_keys_active ON api_keys(is_active);

-- Insertion de la clé admin par défaut
INSERT INTO api_keys (key_hash, role, description)
VALUES (
    sha256('admin-default-key-change-me'),
    'admin',
    'Default admin key - CHANGE ME'
) ON CONFLICT (key_hash) DO NOTHING;


-- Table de suivi des tâches d'ingestion (Phase 1)
CREATE TABLE IF NOT EXISTS ingestion_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status VARCHAR(30) NOT NULL DEFAULT 'UPLOADED',
    files JSONB NOT NULL,
    metadata JSONB NOT NULL,
    chunks JSONB,
    options JSONB NOT NULL,
    admin_id INTEGER REFERENCES api_keys(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    error_message TEXT
);

CREATE INDEX idx_ingestion_tasks_status ON ingestion_tasks(status);
CREATE INDEX idx_ingestion_tasks_created_at ON ingestion_tasks(created_at);