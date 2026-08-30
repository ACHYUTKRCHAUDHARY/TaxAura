-- Run this migration against PostgreSQL before enabling document/RAG APIs.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE documents (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    checksum CHAR(64) NOT NULL,
    extracted_text TEXT,
    processing_status VARCHAR(30) NOT NULL DEFAULT 'QUEUED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- B-tree: user-scoped document listing and recent-upload retrieval.
CREATE INDEX idx_documents_user_created_at ON documents(user_id, created_at DESC);
-- Hash: only exact checksum duplicate detection; B-tree remains the general default.
CREATE INDEX idx_documents_checksum_hash ON documents USING HASH(checksum);
-- GIN inverted index: fast keyword/full-text search over OCR text.
CREATE INDEX idx_documents_extracted_text_fts
ON documents USING GIN (to_tsvector('english', coalesce(extracted_text, '')));

CREATE TABLE tax_rule_chunks (
    id UUID PRIMARY KEY,
    source_name VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tax_rule_chunks_fts
ON tax_rule_chunks USING GIN (to_tsvector('english', content));
-- HNSW: approximate nearest-neighbour retrieval for RAG semantic search.
CREATE INDEX idx_tax_rule_chunks_embedding_hnsw
ON tax_rule_chunks USING hnsw (embedding vector_cosine_ops);
