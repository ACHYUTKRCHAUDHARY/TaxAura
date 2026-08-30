## TaxAura

Indian tax-assistance backend built with FastAPI and PostgreSQL.

### First workflow: document upload

`POST /api/v1/documents/upload?user_id=<uuid>` accepts a PDF/JPEG/PNG and queues it for OCR and indexing. The current endpoint validates the upload; persistent storage, OCR, embeddings, RAG retrieval, and n8n notifications are implemented in later milestones.

### Database retrieval indexes

Run `src/aura/db/migrations/001_initial_retrieval_schema.sql` in a PostgreSQL database with the `pgvector` extension available.

- B-tree: user-scoped document lookup and sorting
- Hash: exact document checksum duplicate lookup
- GIN: OCR/tax-rule keyword search
- HNSW: semantic RAG retrieval
