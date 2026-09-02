# TaxAura

TaxAura is a FastAPI-based Indian tax-assistance MVP. It combines deterministic tax comparison, document OCR, PostgreSQL full-text/vector retrieval, local RAG with Ollama, n8n workflow events, and a controlled LangGraph advisor.

> TaxAura is an educational estimator, not professional tax or filing advice.

## Architecture

```text
Client -> FastAPI -> PostgreSQL + pgvector
                 -> OCR -> document chunks -> embeddings
                 -> RAG -> Ollama -> cited answer
                 -> deterministic tax calculator
                 -> n8n webhook -> notification workflow
```

## Features

- Create and retrieve users
- Upload PDF/JPEG/PNG tax documents
- Extract PDF text or run Tesseract OCR on images
- Track `QUEUED -> PROCESSING -> COMPLETED/FAILED` status
- B-tree, hash, GIN full-text, and HNSW vector indexes
- Ingest verified tax-rule content and ask grounded RAG questions
- Compare old and new regimes for AY 2026-27
- Publish document completion/failure events to n8n
- Optional controlled LangGraph + Ollama advisor

## Windows setup

Requirements: Python 3.14, `uv`, PostgreSQL with pgvector, Ollama, and Tesseract OCR for image uploads.

```powershell
git clone https://github.com/ACHYUTKRCHAUDHARY/TaxAura.git
cd TaxAura
uv sync --dev
Copy-Item .env.example .env
```

Create a PostgreSQL database named `taxaura`, enable pgvector, then run the SQL in:

```text
src/aura/db/migrations/001_initial_retrieval_schema.sql
```

Install and start local models:

```powershell
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
ollama serve
```

For image OCR, install Tesseract and put its executable path in `.env`:

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

Start the API:

```powershell
uv run uvicorn aura.main:app --reload
```

Open Swagger UI: `http://127.0.0.1:8000/docs`.

## Main APIs

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/users` | Create a user |
| GET | `/api/v1/users/{user_id}` | Get a user |
| POST | `/api/v1/documents/upload?user_id=...` | Upload and process a document |
| GET | `/api/v1/documents?user_id=...` | List user documents |
| GET | `/api/v1/documents/{id}?user_id=...` | Check document status |
| POST | `/api/v1/tax/compare` | Compare old/new regime estimates |
| POST | `/api/v1/knowledge/rules` | Ingest verified tax-rule text |
| POST | `/api/v1/knowledge/ask` | Ask a cited RAG question |
| POST | `/api/v1/advisor/ask` | Use the controlled agent |

## n8n

Import `n8n/workflows/document-notifications.json` into n8n, activate it, and set its production webhook URL as `N8N_WEBHOOK_URL` in `.env`. TaxAura emits `document.completed` and `document.failed` events. Add email, Telegram, or other notification nodes after the webhook as needed.

## Database retrieval strategy

- B-tree: user/document relationships and date ordering
- Hash: exact SHA-256 checksum lookup
- GIN: keyword/full-text search
- HNSW: semantic vector retrieval with 768-dimensional `nomic-embed-text` vectors

## Tax-calculator scope

The deterministic calculator targets a resident salaried individual below age 60 for AY 2026-27 and income up to ₹50 lakh. It applies standard deductions, section 87A rebate, and 4% cess. It does not yet handle marginal relief, surcharge, capital gains, special-rate income, or every deduction rule.

Official references:

- https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1
- https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-2

## Verification

```powershell
uv run ruff check src tests
uv run pytest
```

## Next production steps

- Add JWT authentication and replace query-string `user_id` with authenticated identity
- Protect tax-rule ingestion with an admin role
- Move uploads to encrypted object storage
- Add malware scanning, rate limits, audit logs, and secret management
- Use a durable worker queue instead of in-process background tasks
