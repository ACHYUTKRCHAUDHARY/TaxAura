from contextlib import asynccontextmanager

from fastapi import FastAPI

from aura.api.router import api_router
from aura.db.session import close_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await close_database()


app = FastAPI(
    title="Aura API",
    description="AI-powered Indian tax assistant with RAG, document processing, and automation.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "Welcome to TaxAura API", "docs": "/docs"}


@app.get("/health")
def health_check():
    return {"status": "UP"}
