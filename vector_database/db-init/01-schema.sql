CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id        SERIAL PRIMARY KEY,
    content   TEXT,
    metadata  JSONB,
    embedding vector(2048)  -- ← CHANGÉ de 1024 à 2048
);

CREATE INDEX hnsw_index
on documents 
USING hnsw (embedding vector_cosine_ops);