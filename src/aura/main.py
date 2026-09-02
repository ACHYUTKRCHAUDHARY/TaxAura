from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles

from aura.api.router import api_router
from aura.core.config import settings
from aura.core.logging import configure_logging
from aura.core.middleware import SecurityHeadersMiddleware
from aura.db.session import close_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    yield
    await close_database()


app = FastAPI(
    title="Aura API",
    description="AI-powered Indian tax assistant with RAG, document processing, and automation.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api/v1")
if settings.frontend_directory.exists():
    app.mount(
        "/app",
        StaticFiles(directory=settings.frontend_directory, html=True),
        name="frontend",
    )
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
    return {"message": "Welcome to TaxAura API", "frontend": "/app", "docs": "/docs"}


@app.get("/health")
def health_check():
    return {"status": "UP"}
