# TaxAura

Indian tax assistance with **Next.js + TypeScript + TanStack Query**, **FastAPI**, **PostgreSQL + pgvector**, and **Gemini**.

Production: Vercel Next.js → Render FastAPI → PostgreSQL/pgvector, with server-side Gemini for generated answers. One database stores accounts, uploads, extracted text, chunks, and vectors. MiniLM embeddings run locally inside the backend; no embedding API account is needed.

The calculator targets FY 2025–26 / AY 2026–27 resident salaried individuals below 60 with salary up to ₹50 lakh. It is an educational estimator, not a tax-filing service.

## Run on Windows with Docker Desktop

Enable Docker Desktop's WSL2 backend, then:

```powershell
git clone https://github.com/ACHYUTKRCHAUDHARY/TaxAura.git
cd TaxAura
Copy-Item .env.example .env
```

Generate a JWT signing secret:

```powershell
$bytes = New-Object byte[] 48
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes)
[Convert]::ToBase64String($bytes)
$rng.Dispose()
```

Paste the result into `.env` as `JWT_SECRET_KEY`; add your Google AI Studio key as `GEMINI_API_KEY`. Leaving the Gemini key empty enables source excerpts instead of generated answers.

```powershell
docker compose up --build
```

Open **http://localhost:8080/**. The three services are Next.js, FastAPI, and PostgreSQL 17 with pgvector 0.8.2. The first backend build downloads and bakes the local MiniLM model into its image. Startup runs Alembic and Uvicorn with Render-compatible `PORT` handling.

```powershell
docker compose exec app .venv/bin/python -m aura.scripts.seed_knowledge
docker compose exec app .venv/bin/python -m aura.scripts.create_admin --email you@example.com --name "TaxAura Admin"
```

Register/login, upload documents, preview extracted text, retry failures, delete documents, compare regimes, and ask source-linked questions. Administrators can add reviewed public tax guidance. The Next.js UI and API request/response contracts are preserved.

## Data and retrieval

- PostgreSQL owns durable uploads and all vector data, in the `postgres_data` volume.
- `document_chunks` retains its IDs, document/user links, content, and creation timestamp; it adds `chunk_index`, `embedding vector(384)`, and `embedding_model`.
- `tax_rule_chunks` retains source names/URLs and content; it adds the same vector and model fields.
- Embeddings use `sentence-transformers/all-MiniLM-L6-v2` through FastEmbed/ONNX on CPU, normalized to 384 dimensions. The version marker is `minilm-l6-v2-fastembed-v1`.
- Rule retrieval uses cosine distance with an HNSW index. Private retrieval materializes the authenticated owner's completed chunks first, then performs exact cosine top-K to avoid global approximate-search filtering losing results. Both chunk and document ownership must match.
- Embeddings are written in the same transaction as their source rows. Document deletion cascades to chunks and embeddings atomically.
- If local model inference fails, extracted text is retained and PostgreSQL full-text retrieval remains available. Admin ingestion returns `semantic_indexed=false`. Database errors propagate as failures, rather than fabricated empty search results.
- General questions and reviewed rule excerpts may be sent to Gemini. **“Include my documents” remains local excerpt mode**, preserving the existing privacy behavior. Private uploads are not sent to Gemini for embedding or answers in that mode.

Uploads support text PDFs and PNG/JPEG OCR. Convert scanned image-only PDFs to images first. Limits: 10 MB per upload in Docker, 4 MB through Vercel, 50 documents per user, PDFs up to 100 pages/200,000 extracted characters.

## Upgrade an existing installation

Back up the database before upgrading. Revision `20261001_03` enables `vector`, adds nullable vector columns, backfills stable chunk positions, and creates indexes. Existing document bytes, text, IDs, and account data remain intact. **Run reindex once after migration** to populate vectors from existing PostgreSQL chunk text:

```powershell
docker compose exec app .venv/bin/python -m aura.scripts.reindex
docker compose exec app .venv/bin/python -m aura.scripts.verify_vectors
```

Reindex updates rows in batches and can safely be rerun. Legacy chunk order is assigned by `(created_at, id)` because the previous schema did not store positions; new uploads retain extraction order. Do not change the embedding model/dimensions without a matching schema migration and complete reindex.

## Frontend development

Install Node.js 22. With the Docker backend running on port 10000:

```powershell
cd frontend
Copy-Item .env.example .env.local
npm ci
npm run dev
```

Open http://localhost:3000/. `API_ORIGIN` is server-side and defaults to `http://127.0.0.1:10000`. Never put database, JWT, or Gemini secrets in `NEXT_PUBLIC_*` variables.

## Hosting and configuration

Deploy `frontend/` to Vercel and the root Dockerfile to Render. Set Render's `DATABASE_URL` to a persistent PostgreSQL database with the vector extension available. Set Vercel's `API_ORIGIN` to the Render backend URL. See [deployment instructions](docs/DEPLOYMENT.md) for exact settings, migrations, extension privileges, and provider limits.

Required production backend settings: `DATABASE_URL`, `JWT_SECRET_KEY`, `ENVIRONMENT=production`, and `ALLOWED_HOSTS`. Add `GEMINI_API_KEY` for generation. `GEMINI_MODEL` retains its existing default; `ALLOWED_ORIGINS` can be empty when the frontend proxy is used. Optional `EMBEDDING_CACHE_DIR` controls only the local model-weight cache, not vector storage.

`/health` checks the process. `/ready` checks PostgreSQL, both vector columns/operators, and the expected Alembic revision. It never calls Gemini. To inspect the stack:

```powershell
docker compose ps
docker compose logs -f app
docker compose down
```

`docker compose down` retains data; `docker compose down -v` destroys volumes. Backups are your responsibility.

## Verification

```powershell
uv sync --frozen --dev
uv run ruff check src tests
uv run pytest -q
cd frontend
npm ci
npm run build
npm run typecheck
npx playwright install chromium
npm run test:e2e
```

Database integration tests need a **disposable, migrated** `TEST_DATABASE_URL`. Without it they are explicitly skipped. CI tests fresh migrations, existing-data upgrades, downgrade/re-upgrade, embedding persistence, cosine ranking, document isolation, atomic deletion, backfill, keyword fallback, database failures, and mocked Gemini failures.

Compose CI builds the real three-service stack, uses real MiniLM embeddings, seeds the database, verifies stored vectors, and runs browser journeys including real PDF ingestion, private retrieval, cross-user denial, tax comparison, and admin ingestion. `npm run test:live` targets a disposable seeded stack on port 8080; it creates test accounts/content. Set `E2E_ADMIN_EMAIL` and `E2E_ADMIN_PASSWORD` to include the admin journey. Live Gemini responses require your own API key and are not claimed by mocked tests.
