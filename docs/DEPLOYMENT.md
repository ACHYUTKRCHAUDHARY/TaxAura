# Self-hosted TaxAura with Gemini

## Local Docker setup

1. Install Docker Desktop on Windows with the WSL2 backend.
2. Clone the repository and copy `.env.example` to `.env`.
3. Set a random `JWT_SECRET_KEY` using the README's PowerShell command.
4. Add your server-side `GEMINI_API_KEY` from Google AI Studio. Leave it empty to use source excerpts without generation.
5. Run `docker compose up --build`.
6. Open http://localhost:8080/.
7. Load knowledge and create an admin:

```powershell
docker compose exec app .venv/bin/python -m aura.scripts.seed_knowledge
docker compose exec app .venv/bin/python -m aura.scripts.create_admin --email you@example.com --name "TaxAura Admin"
```

The app waits for PostgreSQL health and probes Chroma's `/api/v2/heartbeat`, applies migrations, then starts one Uvicorn worker. App and Chroma ports bind only to localhost. PostgreSQL has no published host port. The bundled database password is for local development only.

## Persistent data

- PostgreSQL 17: `postgres_data` at `/var/lib/postgresql/data`.
- Chroma 1.5.9: `chroma_data` at `/data`.
- Upload bytes and extracted text live in PostgreSQL. Vector records live in Chroma.
- Embeddings use all-MiniLM-L6-v2 locally; no Gemini embedding API calls are needed.

Named volumes survive container restarts, image rebuilds, and `docker compose down`. They do not survive `docker compose down -v`, deliberate volume removal, or losing the host disk. Back up your data before host/image upgrades. Use a new collection and reindex if you change embedding models.

## Use an existing PostgreSQL database

Set `DATABASE_URL` in `.env` to its direct asyncpg-compatible connection string, for example:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/DATABASE?ssl=verify-full
```

Percent-encode special characters in credentials. Asyncpg accepts `ssl`, not libpq-only `sslmode` or `channel_binding` query parameters. Use your provider's TLS instructions.

By default the unused local Postgres service still starts. With Docker Compose 2.24.4 or later, create `compose.external-db.yml`:

```yaml
services:
  postgres:
    profiles: [bundled-database]
  app:
    depends_on: !override
      chroma:
        condition: service_started
```

Then run:

```powershell
docker compose -f docker-compose.yml -f compose.external-db.yml up --build
```

Inside containers, `localhost` means that container. To reach PostgreSQL installed directly on your Windows host, use `host.docker.internal` as the database hostname.

## Gemini configuration

The app uses `langchain-google-genai`, which calls Google's Gemini API. `GEMINI_API_KEY` stays on the backend. `GEMINI_MODEL` defaults to `gemini-3.8-flash` and can be overridden with a model available to your project. Generation requests have a 45-second total timeout and no automatic model retries. RAG falls back to excerpts on missing credentials, quota exhaustion, unavailable models, or empty responses. The agent endpoint can return 503 if its tool-driven run fails.

The `.env` template also contains `JWT_SECRET_KEY` because removing it would break authenticated production startup. Database connection settings alone cannot configure the whole app.

General chat sends the question and selected reviewed tax rules to Gemini. Private document queries return local excerpts; raw uploads, filenames, and extracted personal document content are not sent by that flow. Do not type sensitive details into a general question. The advisor's status tool returns numbered statuses, not filenames. Add only public, reviewed guidance through admin knowledge ingestion.

Google's free tier has rate/model limits, and its pricing page says free-tier content may be used to improve products. Paid usage has different terms. Confirm eligibility and limits in your own project; no code change can guarantee unlimited free API usage.

## Free hosting choices

**Local machine:** this is the supplied, persistent setup without a cloud hosting bill. It is available while Docker and your computer are running. Gemini still needs internet and remains subject to quota. The local embedding model downloads during the first image build.

**Your own VM:** run the same Compose stack on a VM that has sufficient memory and persistent storage. Free VM offers depend on account eligibility, region, capacity, and provider terms; this project does not provision or promise one. Keep the default localhost bindings and access the app through an SSH tunnel, or deliberately configure TLS/reverse proxy, firewall, strong database credentials, exact allowed hosts, backups, and abuse controls for a public deployment. Never expose the unauthenticated Chroma port publicly.

**Render Free:** free web services cannot attach persistent disks. Their filesystem is ephemeral; local Chroma/PostgreSQL data would be lost across replacement/redeployment. Render also does not launch `docker-compose.yml` as one service. The app-only `render.yaml` requires external persistent PostgreSQL and Chroma services, and a reachable secured Chroma endpoint. Its default TLS setting must match the external endpoint/port. A private localhost Chroma instance on your laptop is not reachable from Render. Prefer the local Compose stack for the requested free self-hosted setup.

## Vercel frontend + Render API

The website is now a separate Next.js application in `frontend/`. FastAPI serves APIs only; it no longer serves source files or HTML. Old `/app/*.html` website links redirect to the new pages on the frontend.

1. Deploy the backend using the root `Dockerfile` and `render.yaml`. Supply persistent PostgreSQL and Chroma connections, your Gemini key, and a random JWT secret. Verify `https://YOUR-API.onrender.com/ready` returns `READY` before deploying the frontend.
2. In Vercel, import this GitHub repository. Set **Root Directory** to **frontend** and **Framework Preset** to **Next.js**. Use Node.js **22.x**, install command `npm ci`, and build command `npm run build`. Keep the framework's default output setting; do not set `out` or `.next/standalone` as the output directory.
3. Set these environment variables for Production and Preview:

   ```env
   API_ORIGIN=https://YOUR-API.onrender.com
   NEXT_PUBLIC_MAX_UPLOAD_MB=4
   ```

   `API_ORIGIN` is only the origin: no trailing `/api/v1`. Do not add `NEXT_PUBLIC_` to it. Never put `GEMINI_API_KEY`, the JWT signing secret, database credentials, or Chroma credentials in frontend variables.
4. Deploy. Visit the Vercel URL, register, compare tax estimates, and upload a small PDF. The browser calls same-origin `/api/v1/*`; the Next.js server forwards only supported API routes to FastAPI with the bearer token. CORS can remain empty because the proxy makes the cross-host request server-side. Render's `ALLOWED_HOSTS` must include the actual API hostname.
5. Seed the backend knowledge and create an administrator using its shell or an authenticated environment connected to the same database. The commands are `python -m aura.scripts.seed_knowledge` and `python -m aura.scripts.create_admin --email you@example.com --name "TaxAura Admin"` in the installed backend environment. For Docker use `.venv/bin/python`.

Vercel Functions impose a 4.5 MB request-body limit, so Vercel uploads are capped at **4 MB** to leave room for multipart overhead. Self-hosted Docker builds default to **10 MB**. `NEXT_PUBLIC_MAX_UPLOAD_MB` is a build-time setting; rebuild after changing it. The backend still independently enforces its own file size limit.

The proxy permits up to 55 seconds for API responses; general Gemini generation has its own 45-second backend timeout. A sleeping Render Free service can cause the first request to fail; wait for `/ready` and retry. Persistent Chroma requires a separate persistent service or VM; Vercel does not host Chroma. A public, unauthenticated Chroma endpoint is not a safe deployment.

For local production: `docker compose up --build` runs Next.js on port 8080, FastAPI on port 10000, PostgreSQL, and Chroma. For frontend development against that stack, use `frontend/.env.local` with `API_ORIGIN=http://127.0.0.1:10000`, then `npm run dev` in `frontend/`.

## Verification after startup

```powershell
Invoke-RestMethod http://localhost:10000/health
Invoke-RestMethod http://localhost:10000/ready
docker compose ps
```

Register, sign in, upload a text PDF, wait for completion, preview its text, compare tax regimes, and ask a seeded-rule question. Check source labels. Try “Include my documents”; it should return excerpts rather than generated content. Delete the upload, restart containers without deleting volumes, and confirm remaining data persists.

## Troubleshooting

- App exits immediately: replace the JWT placeholder; inspect `docker compose logs app`.
- Chroma startup timeout: verify `CHROMA_HOST=chroma`, `CHROMA_PORT=8000`, and `docker compose logs chroma`.
- Source excerpts instead of generation: check Gemini key/model/quota and app logs. Never paste keys into issues.
- No matching source: run the seed command or ingest reviewed public guidance as admin.
- Semantic search unavailable: verify Chroma persistence/connectivity and run `docker compose exec app .venv/bin/python -m aura.scripts.reindex`.
- First image build cannot download MiniLM: restore internet access to the model download host and rebuild. No model downloads use Gemini quota.
- Existing release upgrade: back up PostgreSQL. Older filesystem uploads must remain available or be re-uploaded; old vector columns removed by the previous migration require reindexing into the new self-hosted Chroma service.
- Failed document processing: text PDFs and clear images are supported; scanned PDFs must be converted to images. Account/file/page limits are documented in the README.

References: [Chroma Docker](https://docs.trychroma.com/deployment/docker), [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing), [Gemini API keys](https://ai.google.dev/gemini-api/docs/api-key), [Render free limits](https://render.com/docs/free), [Vercel function limits](https://vercel.com/docs/functions/limitations), [Next.js deployment](https://nextjs.org/docs/app/getting-started/deploying).
