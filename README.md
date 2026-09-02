# TaxAura

TaxAura is a production-hardened FastAPI monolith for Indian tax assistance. It combines JWT authentication, deterministic tax comparison, secure document OCR, PostgreSQL full-text/vector retrieval, local RAG with Ollama, n8n workflow events, and a controlled LangGraph advisor.

The responsive frontend is built with HTML, CSS, and Vanilla JavaScript and is served by FastAPI from `/app`.

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

- Argon2 password hashing and expiring JWT access tokens
- User/admin role-based authorization and user-data isolation
- Stream and validate PDF/JPEG/PNG uploads using file signatures
- Extract PDF text or run Tesseract OCR on images
- Track `QUEUED -> PROCESSING -> COMPLETED/FAILED` status
- B-tree, hash, GIN full-text, and HNSW vector indexes
- Ingest verified tax-rule content and ask grounded RAG questions
- Compare old and new regimes for AY 2026-27
- Publish document completion/failure events to n8n
- Optional controlled LangGraph + Ollama advisor
- Responsive landing, authentication, dashboard, calculator, RAG chat, and admin screens

## Windows setup

Requirements: Python 3.14, `uv`, PostgreSQL with pgvector, Ollama, and Tesseract OCR for image uploads.

```powershell
git clone https://github.com/ACHYUTKRCHAUDHARY/TaxAura.git
cd TaxAura
uv sync --dev
Copy-Item .env.example .env
```

Set a unique `JWT_SECRET_KEY` in `.env`, create a PostgreSQL database named `taxaura`, then apply the versioned migration:

```powershell
uv run alembic upgrade head
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

Open the application at `http://127.0.0.1:8000/app/` or Swagger UI at `http://127.0.0.1:8000/docs`.

Create the first administrator:

```powershell
uv run python -m aura.scripts.create_admin --email admin@example.com --name "TaxAura Admin"
```

## Main APIs

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/auth/register` | Register and receive a JWT |
| POST | `/api/v1/auth/login` | Log in using email as `username` |
| GET | `/api/v1/users/me` | Get the authenticated user |
| POST | `/api/v1/documents/upload` | Upload and process your document |
| GET | `/api/v1/documents` | List your documents |
| GET | `/api/v1/documents/{id}` | Check your document status |
| POST | `/api/v1/tax/compare` | Compare old/new regime estimates |
| POST | `/api/v1/knowledge/rules` | Admin-only verified-rule ingestion |
| POST | `/api/v1/knowledge/ask` | Ask a cited RAG question |
| POST | `/api/v1/advisor/ask` | Use the controlled agent |

## Frontend structure

```text
frontend/
├── index.html
├── login.html
├── register.html
├── dashboard.html
├── admin.html
├── css/styles.css
└── js/
    ├── api.js
    ├── auth.js
    ├── dashboard.js
    └── admin.js
```

The browser stores the short-lived access token in `sessionStorage`, sends it as a Bearer token, and clears it when the browser tab session ends or the user logs out.

## n8n

Import `n8n/workflows/document-notifications.json` into n8n, activate it, and set its production webhook URL and a strong shared secret as `N8N_WEBHOOK_URL` and `N8N_WEBHOOK_SECRET` in `.env`. TaxAura signs each body with HMAC-SHA256 in `X-TaxAura-Signature`; verify that signature in n8n before adding notification nodes. TaxAura emits `document.completed` and `document.failed` events.

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

## Production controls included

- Production startup rejects the placeholder JWT secret
- CORS and allowed-host lists come from the environment
- Security headers and request IDs are attached to responses
- Password hashes never leave the API
- Tax-rule ingestion requires the `ADMIN` role
- Document reads and uploads derive identity from JWT, not client-supplied user IDs
- Uploads are streamed, size-limited, signature-checked, randomly named, and private on disk
- Alembic manages schema versions

## Infrastructure steps before public deployment

- Move uploads to encrypted object storage
- Add malware scanning, distributed rate limits, audit logs, and managed secret storage
- Use a durable worker queue instead of in-process background tasks
- Put the API behind TLS and a reverse proxy/load balancer
