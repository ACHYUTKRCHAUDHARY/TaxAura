# Deploy TaxAura: Render + PostgreSQL + ChromaDB

The frontend and API run together on Render. You do not need Vercel, Docker Desktop, or Linux on your Windows computer. Render builds the included Dockerfile remotely; it installs Tesseract OCR and the Chroma embedding model.

## 1. Get the completed code

Merge the completion pull request into `main` (or choose its branch for a preview deployment). Pull the merged changes:

```powershell
git pull origin main
uv sync --frozen
```

## 2. Provision data services

Create a managed PostgreSQL database with your preferred provider and copy its **direct, non-pooler** connection URL. No pgvector extension is required. Keep the database credentials private. Use TLS for an external database:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/DATABASE?ssl=require
```

Percent-encode special characters in the username/password. For this asyncpg driver, use `ssl=require` instead of `sslmode=require` and omit libpq-only parameters such as `channel_binding`. For certificate and hostname verification, use `ssl=verify-full` with a provider trusted by the system CA store.

Create a database in [Chroma Cloud](https://www.trychroma.com/) and obtain:

```env
CHROMA_MODE=cloud
CHROMA_API_KEY=your-private-key
CHROMA_TENANT=your-tenant-id
CHROMA_DATABASE=your-database-name
```

PostgreSQL stores users, upload bytes, extracted text, and chunks. Chroma stores vectors, chunk IDs, and ownership metadata. Chroma embedding inference runs in the app using all-MiniLM-L6-v2; Chroma Cloud does not automatically provide the language model. Keep Chroma credentials server-side. Configure database backups and retention with your providers.

## 3. Deploy the Blueprint

After `render.yaml` is merged into `main`, open:

https://dashboard.render.com/blueprint/new?repo=https://github.com/ACHYUTKRCHAUDHARY/TaxAura

Connect GitHub, select the repository, fill in `DATABASE_URL` and the three Chroma credentials, review the configuration, then click **Apply**. The Blueprint generates a JWT secret. Do not rotate it unintentionally or existing login tokens will stop working.

The provided Blueprint selects Render's free web plan for a demo; verify current provider limits and billing before applying. Chroma Cloud and PostgreSQL are separate services, and their plans are not included. CPU-based embeddings may require a larger Render instance. An idle free service may suspend; queued jobs resume when the app runs again. For continuous background processing, select an always-on paid service. There is no promise of a permanently free production deployment.

The start script runs `alembic upgrade head` then starts one Uvicorn worker on `$PORT`. Use `/ready` as the health check. This checks the database schema; optional AI/Chroma outages degrade to keyword/source-excerpt mode rather than failing the app.

Set `ALLOWED_HOSTS` to your exact `your-service.onrender.com` hostname after deployment. Add any custom hostname explicitly. The Blueprint initially permits `*.onrender.com`. Leave `ALLOWED_ORIGINS` empty for this same-origin frontend.

Open `https://YOUR-SERVICE.onrender.com/app/`.

## 4. Create an admin and load knowledge

You can run these from Windows with a local `.env` that points to the deployed PostgreSQL and Chroma services, or from a Render shell if your plan offers one:

```powershell
uv run python -m aura.scripts.create_admin --email you@example.com --name "TaxAura Admin"
uv run python -m aura.scripts.seed_knowledge
```

The admin command prompts for a password. Sign in at `/app/login.html`. The admin knowledge page accepts a source name, official URL, and reviewed text. The included starter summary is intentionally small and dated to AY 2026-27; add reviewed material for the questions you want the assistant to cover.

## 5. Enable generated answers (optional)

The default `AI_MODE=extractive` returns matching source excerpts, explicitly labeled. Chroma semantic search works independently of Ollama.

For generated RAG answers and the LangGraph advisor, run Ollama on a separate host reachable privately from the app, install `qwen2.5:3b`, and set:

```env
AI_MODE=ollama
OLLAMA_BASE_URL=http://YOUR-PRIVATE-OLLAMA-HOST:11434
OLLAMA_MODEL=qwen2.5:3b
AI_TIMEOUT_SECONDS=45
```

`localhost` on Render refers to the Render container, not your laptop. Do not expose an unauthenticated Ollama endpoint on the public internet. If your model host requires a specific authentication scheme, add that integration before connecting it. If Ollama is unavailable, the RAG endpoint returns labeled excerpts; the agent endpoint returns a service-unavailable error. The dashboard uses the RAG endpoint; `/api/v1/advisor/ask` is available separately.

## 6. Verify the deployment

1. `/health` and `/ready` return HTTP 200.
2. Register, log out, log in, and open the dashboard.
3. Upload a text PDF or a clear PNG/JPEG; wait for COMPLETED, then View text.
4. Log in as a second user and confirm the first user's uploads are absent.
5. Compare salary ₹13,00,000: new-regime estimate should be ₹26,000 for the supported AY 2026-27 scope.
6. Ask about a seeded rule; confirm source names/links. Check “Include my documents” only when you want personal context used.
7. Delete a document and confirm it disappears.
8. Restart the service and confirm accounts and completed uploads remain.

## Operations and limitations

- Chroma indexes are rebuildable: `uv run python -m aura.scripts.reindex`. Run maintenance with document writes paused to avoid concurrent index rebuild/delete races. Never change embedding models in an existing collection without a new collection name and full reindex.
- If Chroma indexing fails, document extraction still completes and keyword search remains available. Run reindex after recovery. Index completion is not part of the COMPLETED document status.
- New uploads are stored in PostgreSQL, with a default 10 MB file limit and 50 documents per account. Temporary files are removed after persistence. This is a bounded small-app design; use private object storage and quotas for large workloads.
- Existing uploads from the old version still use their original filesystem paths. Keep those files available during migration; do not delete old storage until all needed files have been re-uploaded into durable storage. Existing extracted text survives migration.
- Migration `20260929_02` removes old pgvector embedding columns; take a backup first. Rebuild embeddings with the Chroma reindex command. Downgrading does not restore deleted vectors.
- Text PDFs (up to 100 pages / 200,000 extracted characters) and image OCR are supported. Scanned image-only PDFs must first be converted to PNG/JPEG. Password-protected PDFs must be unlocked before upload.
- Jobs are claimed with PostgreSQL row locks in a transaction. A crashed worker leaves the job queued. The UI shows QUEUED until processing commits; failures can be retried manually.
- Optional n8n events are best-effort, not a durable notification outbox. Configure `N8N_WEBHOOK_URL` and `N8N_WEBHOOK_SECRET` only when the receiver verifies the HMAC signature.
- This is not a tax filing system. It excludes special-rate income, capital gains, surcharge, senior-citizen variations and many deduction rules. It supports resident salaried individuals below 60 for FY 2025-26 / AY 2026-27 and salary up to ₹50 lakh.
- Before opening unrestricted public signup, add edge rate limiting/abuse protection, verified-email recovery, monitoring, malware scanning and a documented retention policy. No load test, penetration test, or live cloud deployment is implied by the repository tests.

References: [Render Docker](https://render.com/docs/docker), [health checks](https://render.com/docs/health-checks), [free services](https://render.com/docs/free), [Chroma clients](https://docs.trychroma.com/reference/python), [official tax guidance](https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1).
