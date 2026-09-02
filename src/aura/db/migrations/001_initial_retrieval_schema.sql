-- Fresh TaxAura database schema.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(120) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'USER',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    storage_path VARCHAR(500) NOT NULL,
    checksum CHAR(64) NOT NULL,
    extracted_text TEXT,
    processing_status VARCHAR(30) NOT NULL DEFAULT 'QUEUED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tax_rule_chunks (
    id UUID PRIMARY KEY,
    source_name VARCHAR(255) NOT NULL,
    source_url VARCHAR(1000),
    content TEXT NOT NULL,
    embedding vector(768),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    embedding vector(768),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_documents_user_created_at ON documents(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_document_chunks_user_document ON document_chunks(user_id, document_id);
CREATE INDEX IF NOT EXISTS idx_documents_checksum_hash ON documents USING HASH(checksum);
CREATE INDEX IF NOT EXISTS idx_documents_extracted_text_fts ON documents USING GIN (to_tsvector('english', coalesce(extracted_text, '')));
CREATE INDEX IF NOT EXISTS idx_tax_rule_chunks_fts ON tax_rule_chunks USING GIN (to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_document_chunks_fts ON document_chunks USING GIN (to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_tax_rule_chunks_embedding_hnsw ON tax_rule_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw ON document_chunks USING hnsw (embedding vector_cosine_ops);
