import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from aura.api.router import api_router
from aura.core.config import settings
from aura.core.logging import configure_logging
from aura.core.middleware import SecurityHeadersMiddleware
from aura.db.session import AsyncSessionFactory, close_database
from aura.services.document_processor import run_document_worker


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    task = asyncio.create_task(run_document_worker()) if settings.document_worker_enabled else None
    try:
        yield
    finally:
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        await close_database()


app = FastAPI(
    title="Aura API",
    description="AI-powered Indian tax assistant with RAG, document processing, and automation.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api/v1")
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


@app.get("/")
def root():
    return {"message": "Welcome to TaxAura API", "docs": "/docs"}


@app.get("/health")
def health_check():
    return {"status": "UP"}


@app.get("/ready")
async def readiness():
    try:
        async with AsyncSessionFactory() as session:
            await session.execute(text("SELECT id FROM documents LIMIT 1"))
        return {"status": "READY"}
    except Exception:  # noqa: BLE001 - optional dependency boundary
        return JSONResponse(status_code=503, content={"status": "NOT_READY"})
