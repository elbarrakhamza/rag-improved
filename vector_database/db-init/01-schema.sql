
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id        SERIAL PRIMARY KEY,
    content   TEXT,
    metadata  JSONB,
    embedding vector(1024)
);

CREATE INDEX hnsw_index
on documents 
USING hnsw (embedding vector_cosine_ops);