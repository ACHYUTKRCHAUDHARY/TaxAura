# TaxAura

An Indian tax-assistance web app built with FastAPI, PostgreSQL, **ChromaDB**, and HTML/CSS/vanilla JavaScript. The app serves its frontend at `/app/` and API at `/api/v1`.

TaxAura is an educational estimator for **FY 2025-26 / AY 2026-27**, not a filing service or professional tax advice.

## Features

- Registration/login with Argon2 password hashing, expiring JWTs, and admin authorization
- Private PDF/JPEG/PNG uploads, signature/size checks, account quotas, and durable PostgreSQL storage
- Restart-safe database processing queue, image OCR, extracted-text preview, status polling, retry, and deletion
- ChromaDB semantic search plus PostgreSQL full-text fallback; private retrieval requires ownership checks
- Source-linked tax Q&A with optional personal-document context
- Explicit source-excerpt mode without an LLM; optional Ollama RAG and identity-bound LangGraph advisor
- Old/new regime comparison including section 87A marginal relief near the new-regime rebate threshold
- Admin knowledge ingestion, starter-source seed command, reindex command, optional signed n8n notifications
- Render Blueprint, Docker build, migrations, readiness checks, and CI with PostgreSQL integration tests

## Run locally on Windows

Install Python 3.14, [uv](https://docs.astral.sh/uv/), and PostgreSQL. Create a database named `taxaura`. No pgvector extension or Docker Desktop is needed.

```powershell
git clone https://github.com/ACHYUTKRCHAUDHARY/TaxAura.git
cd TaxAura
uv sync --frozen --dev
Copy-Item .env.example .env
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Put the generated value in `.env` as `JWT_SECRET_KEY`, and update `DATABASE_URL` with your PostgreSQL credentials. Then:

```powershell
uv run alembic upgrade head
uv run python -m aura.scripts.seed_knowledge
uv run python -m aura.scripts.create_admin --email admin@example.com --name "TaxAura Admin"
uv run uvicorn aura.main:app --reload
```

Open http://127.0.0.1:8000/app/. Local Chroma persists in `storage/chroma`; its first use downloads the all-MiniLM-L6-v2 embedding model. If download/indexing fails, keyword search still works; run `uv run python -m aura.scripts.reindex` after fixing connectivity.

For JPEG/PNG OCR, install Tesseract on Windows and set `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe`. Text PDFs do not require Tesseract. Convert image-only PDFs to PNG/JPEG before uploading.

For generated answers, install/start Ollama, run `ollama pull qwen2.5:3b`, and set `AI_MODE=ollama`. Otherwise responses are clearly labeled source excerpts.

## Deploy

Follow **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for the Render + PostgreSQL + Chroma Cloud setup, required secrets, admin initialization, AI configuration, smoke checks, migration cautions, and service limits. No separate Vercel deployment is needed.

## Architecture

PostgreSQL is authoritative for users, upload bytes, extracted text, and chunks. ChromaDB stores derived vectors and ownership metadata. Semantic hits are checked against database ownership before use. The default embedding function runs locally; raw upload text is not stored in Chroma. Enabling Ollama sends selected retrieved context to the configured model host.

The queue uses `FOR UPDATE SKIP LOCKED` and commits extraction atomically. Restarted jobs remain queued. Indexing failures degrade to keyword retrieval; reindex repairs Chroma later. `/health` checks the process, `/ready` checks database/schema access.

## API summary

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/auth/register` | Register |
| POST | `/api/v1/auth/login` | Login; email in `username` form field |
| GET | `/api/v1/users/me` | Profile |
| POST | `/api/v1/documents/upload` | Upload |
| GET | `/api/v1/documents` | Own documents |
| GET | `/api/v1/documents/{id}/text` | Extracted text |
| POST | `/api/v1/documents/{id}/retry` | Retry failed extraction |
| DELETE | `/api/v1/documents/{id}` | Delete document/chunks/vectors |
| POST | `/api/v1/tax/compare` | Supported tax comparison |
| POST | `/api/v1/knowledge/rules` | Admin ingestion |
| POST | `/api/v1/knowledge/ask` | Cited Q&A; optional `include_documents` |
| POST | `/api/v1/advisor/ask` | Controlled advisor |

## Verification

```powershell
uv run ruff check src tests
uv run pytest -q
```

Integration tests require a disposable migrated PostgreSQL database:

```powershell
$env:TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/taxaura_test"
$env:DATABASE_URL=$env:TEST_DATABASE_URL
$env:CHROMA_MODE="disabled"
uv run alembic upgrade head
uv run pytest -q
```

CI runs this against PostgreSQL 17. Tests disable external AI services. Chroma tests cover ownership filters; full deployment still requires provider credentials and a working embedding download. See the deployment guide for operational boundaries before unrestricted public use.
