# Deploy TaxAura: Vercel + Render + PostgreSQL/pgvector

## Architecture

| Component | Host | Configuration |
|---|---|---|
| Next.js / TypeScript / TanStack Query | Vercel | Root directory `frontend`, server-only `API_ORIGIN` |
| FastAPI + local MiniLM embeddings | Render Docker web service | Root Dockerfile, server-side secrets |
| Relational data and vector embeddings | Persistent PostgreSQL | `DATABASE_URL`, pgvector extension |
| Generated answers | Gemini API | Backend-only `GEMINI_API_KEY` |

The backend is stateless except for temporary upload files and baked model weights. Persistent uploads, chunks, and embeddings all live in PostgreSQL. There is no separate vector service.

## 1. Prepare PostgreSQL

Use PostgreSQL with pgvector **0.8.2 or newer** (the tested Compose version). Your provider must support installation of the `vector` extension. For example, a compatible managed PostgreSQL instance or your own pgvector-enabled PostgreSQL server can be used. This repository does not provision a database account or guarantee a permanent free tier.

A database administrator may need to run this once:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
SELECT extversion FROM pg_extension WHERE extname = 'vector';
```

Alembic also runs the extension command. If your migration user lacks extension privileges, pre-enable it with an administrator. The migration user needs table/index DDL privileges; do not give database credentials to the frontend.

Use an async SQLAlchemy connection string:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/taxaura
```

`postgres://` and `postgresql://` prefixes are normalized to asyncpg. Percent-encode special characters in credentials. For remote TLS use the provider's certificate instructions; asyncpg supports `?ssl=verify-full`, not libpq-only `sslmode` or `channel_binding` URL parameters. Use a direct database connection for migrations.

## 2. Deploy FastAPI on Render

Import the repository as a Blueprint using `render.yaml`, or create a Docker web service with the root `Dockerfile`. Keep the repository root as the build context. Set:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/taxaura
GEMINI_API_KEY=your-server-side-key
GEMINI_MODEL=gemini-3.8-flash
JWT_SECRET_KEY=your-random-secret-at-least-32-characters
ENVIRONMENT=production
ALLOWED_HOSTS=your-api.onrender.com,localhost,127.0.0.1
ALLOWED_ORIGINS=
DOCUMENT_WORKER_ENABLED=true
```

The Blueprint generates a JWT secret for new services. Preserve the existing signing key when upgrading an existing service unless intentionally invalidating sessions. Use a Gemini model available to your account. Missing credentials or Gemini errors produce labeled excerpts in RAG; optional agent requests may return 503.

The image installs dependencies with the lockfile, installs OCR tools, and downloads the MiniLM weights during build. Runtime startup runs:

```sh
uv run --no-sync alembic upgrade head
uv run --no-sync uvicorn aura.main:app --host 0.0.0.0 --port "$PORT" --workers 1
```

`scripts/start.sh` defaults to port 10000 locally and respects Render's injected `PORT`. Health-check path: `/ready`. Check:

```text
https://your-api.onrender.com/health   -> {"status":"UP"}
https://your-api.onrender.com/ready    -> {"status":"READY"}
```

Deploy one API instance initially; the existing worker uses PostgreSQL row locks. Run schema changes once during a controlled deployment if you later scale instances. Ensure the selected Render plan has enough memory for FastAPI, ONNX inference, and OCR; low-memory tiers may require upgrading. No live Render capacity test is implied by Docker CI.

## 3. Migrate and load knowledge

Back up an existing database first. Revision `20261001_03` adds `vector(384)` columns and HNSW cosine indexes to both chunk tables, plus unique ordered document chunk positions. It retains existing text and document bytes; it does not call an embedding provider from inside a migration.

After deploying the revision, use the backend shell:

```sh
.venv/bin/python -m aura.scripts.reindex
.venv/bin/python -m aura.scripts.seed_knowledge
.venv/bin/python -m aura.scripts.verify_vectors
.venv/bin/python -m aura.scripts.create_admin --email you@example.com --name "TaxAura Admin"
```

Reindex is mandatory for existing text chunks and updates in batches of 32. Until it finishes, unembedded rows have keyword-search fallback. Rerunning it does not create duplicate chunks. `verify_vectors` requires seeded/ingested rules and checks stored embeddings plus database retrieval.

If your Render plan does not offer a shell, run the same modules from a trusted local Python environment configured with the production database connection and server-side settings. Do not expose an unauthenticated migration/admin endpoint. To create an administrator, the command prompts for a password; never commit it.

The migration assigns old document chunk positions by creation time and ID because old rows had no explicit ordering. New ingestion stores the true chunk index. Downgrading removes vector columns/indexes and positions but retains text and uploads; re-upgrading then requires reindex again. HNSW index creation is transactional and may lock large existing tables; schedule maintenance for large datasets.

## 4. Deploy Next.js on Vercel

Import the repository and configure:

| Setting | Value |
|---|---|
| Root Directory | `frontend` |
| Framework | Next.js |
| Node.js | 22.x |
| Install Command | `npm ci` |
| Build Command | `npm run build` |
| Output Directory | Framework default |

Environment variables for Production and Preview:

```env
API_ORIGIN=https://your-api.onrender.com
NEXT_PUBLIC_MAX_UPLOAD_MB=4
```

Use only the origin, without `/api/v1`. `API_ORIGIN` stays server-side. Never add Gemini keys, JWT secrets, or database URLs to `NEXT_PUBLIC_*` variables.

The browser calls same-origin `/api/v1/*`; the Next.js server forwards supported paths and bearer authorization to Render. `ALLOWED_ORIGINS` can stay empty for this server-side proxy flow. Backend `ALLOWED_HOSTS` must contain the actual API hostname. Existing frontend routes, authentication, and API response shapes are unchanged.

Vercel's request-body limit is 4.5 MB, so its frontend upload cap stays at 4 MB for multipart overhead. Docker builds retain 10 MB. The upload limit is a build-time frontend setting. The proxy timeout is 55 seconds; Gemini generation has a separate 45-second backend timeout.

## Local Windows development

Use the README's Docker Desktop instructions. Only three services run: `frontend`, `app`, and `postgres` (image `pgvector/pgvector:0.8.2-pg17`). Next.js binds localhost:8080, the API localhost:10000, and PostgreSQL has no published host port. `postgres_data` keeps relational data and vectors across restarts.

To use an existing database, set `DATABASE_URL` in root `.env`. To avoid starting the unused bundled database, with Compose 2.24.4+ create `compose.external-db.yml`:

```yaml
services:
  postgres:
    profiles: [bundled-database]
  app:
    depends_on: !override {}
```

```powershell
docker compose -f docker-compose.yml -f compose.external-db.yml up --build
```

For native Windows Python development: install Python 3.14, uv, PostgreSQL with pgvector, and Tesseract for OCR. Set `.env` to your local database, set `TESSERACT_CMD` if required, then:

```powershell
uv sync --frozen --dev
uv run alembic upgrade head
uv run python -m aura.scripts.seed_knowledge
uv run uvicorn aura.main:app --host 127.0.0.1 --port 10000
```

In another terminal, run `npm ci` and `npm run dev` inside `frontend/`. Its `.env.local` should set `API_ORIGIN=http://127.0.0.1:10000`.

## Operations and limits

- A persistent PostgreSQL service is still required. Render Free web-service filesystems are ephemeral, and free Render PostgreSQL databases expire; do not store production data in container-local files or rely on a temporary database.
- Back up PostgreSQL, including uploads and vectors. Never use `docker compose down -v` on data you need.
- Default embedding cache: `storage/embeddings`; Docker overrides `EMBEDDING_CACHE_DIR` to `/home/app/.cache/fastembed`. It contains model weights only. Do not delete baked weights from a running container.
- Model inference failure preserves text and uses SQL keyword fallback; rerun reindex after recovery. Database failure returns unavailable responses and `/ready` becomes 503. Inspect server logs without publishing secrets.
- Private retrieval checks the authenticated user against both chunk and parent document ownership before cosine ranking. Only completed documents participate. Deletion cascades to vector rows in the same transaction.
- Private-document questions still return local excerpts and are not sent to Gemini. General questions may be sent with reviewed public tax-rule text; avoid personal details in general questions.
- Old filesystem-backed uploads from early releases must be retained or re-uploaded; already extracted chunk text can still be reindexed from PostgreSQL.

References: [pgvector](https://github.com/pgvector/pgvector), [FastEmbed models](https://qdrant.github.io/fastembed/examples/Supported_Models/), [Render free limits](https://render.com/docs/free), [Vercel function limits](https://vercel.com/docs/functions/limitations).
