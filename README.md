# TaxAura

A tax-assistance website with FastAPI, PostgreSQL, self-hosted ChromaDB, Gemini, and a Next.js App Router + TypeScript frontend with TanStack Query. The calculator targets FY 2025-26 / AY 2026-27 resident salaried individuals below 60 with salary up to ₹50 lakh. It is an educational estimator, not a tax-filing service.

## Run on Windows with Docker Desktop

Install Docker Desktop and enable its WSL2 backend. You do not need separate local PostgreSQL, Python, Tesseract, or Chroma installations.

```powershell
git clone https://github.com/ACHYUTKRCHAUDHARY/TaxAura.git
cd TaxAura
Copy-Item .env.example .env
```

Generate a JWT secret using PowerShell:

```powershell
$bytes = New-Object byte[] 48
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes)
[Convert]::ToBase64String($bytes)
$rng.Dispose()
```

Paste it into `.env` as `JWT_SECRET_KEY`. Put your [Google AI Studio key](https://aistudio.google.com/apikey) in `GEMINI_API_KEY`. Keep `.env` private. Leaving the Gemini key empty runs source-excerpt mode.

```powershell
docker compose up --build
```

Wait for the app to start, then open **http://localhost:8080/**. The first build downloads dependencies and the local MiniLM embedding model. In another terminal:

```powershell
docker compose exec app .venv/bin/python -m aura.scripts.seed_knowledge
docker compose exec app .venv/bin/python -m aura.scripts.create_admin --email you@example.com --name "TaxAura Admin"
```

Register or log in. You can upload documents, view extracted text, retry failed uploads, delete documents, compare tax regimes, and ask source-linked questions. Administrators can ingest reviewed tax guidance.

## What runs where

| Component | Location | Persistence |
|---|---|---|
| Next.js website | Frontend container, localhost:8080 | Stateless |
| FastAPI | App container, localhost:10000 | PostgreSQL is the source of truth |
| PostgreSQL | Private Compose network | `postgres_data` named volume |
| ChromaDB | `chroma:8000`, host localhost:8000 | `chroma_data` mounted at `/data` |
| MiniLM embeddings | App container | Model baked into image |
| Gemini answers | Google API | Subject to your account's limits/terms |

The Chroma client uses `HttpClient` with `CHROMA_HOST` and `CHROMA_PORT`. No hosted Chroma account or credentials are needed. Chroma stores derived vectors and ownership metadata; PostgreSQL stores users, private uploads, extracted text, and source chunks.

Gemini is accessed server-side only. The default model is `gemini-3.8-flash`; override with `GEMINI_MODEL` if required by your account. Missing credentials, quota failures, or generation errors fall back to clearly labeled excerpts in the RAG chat. The controlled advisor endpoint has bounded execution and authenticated tool identity.

**Privacy:** general questions and retrieved tax-rule text are sent to Gemini. Do not enter sensitive information into general questions. “Include my documents” uses local excerpts and never sends those documents to Gemini. Gemini's free-tier data terms differ from paid usage; review them before using personal information.

## Configuration

`.env.example` includes the three database connection variables plus two necessary application secrets: the Gemini key and the JWT signing secret. Optional settings include `GEMINI_MODEL`, `AI_MODE=extractive`, and `AI_TIMEOUT_SECONDS` (default 45). Chroma requires no API key.

For an existing PostgreSQL database, replace `DATABASE_URL`; the app uses that database. The bundled Postgres service still starts but is unused. To omit it, use the external-database Compose override documented in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Operations

```powershell
docker compose ps
docker compose logs -f app
docker compose down
docker compose up -d
docker compose exec app .venv/bin/python -m aura.scripts.reindex
```

`docker compose down` keeps data. `docker compose down -v` deletes volumes and all their data. Backend `http://localhost:10000/health` checks the process; `http://localhost:10000/ready` checks PostgreSQL/schema availability. Chroma startup is probed before migrations and API startup.

Uploads support text PDFs and PNG/JPEG OCR. Convert scanned image-only PDFs to images first. Limits: 10 MB per upload, 50 documents per user, PDFs up to 100 pages/200,000 extracted characters. Queue jobs survive app restarts; failed semantic indexing can be repaired with reindex. Existing filesystem uploads from older releases must be retained or re-uploaded.

## Hosting

The provided Compose stack is intended for your local computer or a VM you control. Render Free does not provide persistent disks for these database containers and does not deploy a Compose stack directly. The retained `render.yaml` deploys only the app and requires externally hosted PostgreSQL and ChromaDB.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for persistent hosting, external database use, Gemini configuration, and troubleshooting. Local Docker has no cloud hosting bill; Gemini free quota is limited and not a promise of unlimited free usage.

## Frontend development

Install Node.js 22 LTS. With the backend running on port 10000:

```powershell
cd frontend
Copy-Item .env.example .env.local
npm ci
npm run dev
```

Open http://localhost:3000/. App Router handles pages; TanStack Query handles authenticated API queries, mutations, cache invalidation, and document polling. Authentication uses the existing short-lived bearer token in session storage. Signing out clears the query cache. FastAPI still enforces authentication, roles, and document ownership on every request.

For Vercel, select `frontend` as the root directory, choose Next.js, set server-only `API_ORIGIN` to your Render backend URL, and leave `NEXT_PUBLIC_MAX_UPLOAD_MB=4`. See the complete [Vercel + Render instructions](docs/DEPLOYMENT.md#vercel-frontend--render-api).

## Tests

```powershell
uv sync --frozen --dev
uv run ruff check src tests
uv run pytest -q
```

The PostgreSQL integration test requires a disposable migrated database in `TEST_DATABASE_URL`. CI runs native PostgreSQL tests and builds/starts the actual Compose stack, seeds knowledge, and checks a real Chroma semantic query. Gemini tests mock the API and cover configuration, generation, fallback, and private-document isolation; a live Gemini request requires your key.

Frontend build and browser checks:

```powershell
cd frontend
npm ci
npm run build
npm run typecheck
npx playwright install chromium
npm run test:e2e
```

Browser tests cover complete user flows against a controlled API fixture. Compose CI also runs real browser journeys through Next.js, FastAPI, PostgreSQL, and Chroma: registration, PDF extraction, cross-user access denial, tax comparison, public and private RAG, sign-in persistence, deletion, and admin ingestion. Run `npm run test:live` only against a disposable seeded local stack; it creates test accounts and content. Set `E2E_ADMIN_EMAIL` and `E2E_ADMIN_PASSWORD` to include the admin journey. No live Gemini call runs in CI; generation remains covered by provider-mocked backend tests.
