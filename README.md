## TaxAura

Indian tax-assistance backend built with FastAPI and PostgreSQL.

### First workflow: document upload

`POST /api/v1/documents/upload?user_id=<uuid>` accepts a PDF/JPEG/PNG, stores metadata in PostgreSQL and the original file in `storage/uploads`, then marks it `QUEUED` for OCR and indexing. The supplied user must already exist in the `users` table.

### Database retrieval indexes

Run `src/aura/db/migrations/001_initial_retrieval_schema.sql` in a PostgreSQL database with the `pgvector` extension available.

- B-tree: user-scoped document lookup and sorting
- Hash: exact document checksum duplicate lookup
- GIN: OCR/tax-rule keyword search
- HNSW: semantic RAG retrieval

### Agentic tax advisor

The advisor uses free local technology: LangGraph + Ollama + `qwen2.5:3b`. It can only use controlled tax-rule-search and user-document-status tools.

```bash
ollama pull qwen2.5:3b
ollama serve
uv run uvicorn aura.main:app --reload
```

Use `POST /api/v1/advisor/ask` with `user_id` and `question`.
