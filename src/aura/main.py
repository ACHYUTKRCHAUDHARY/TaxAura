from fastapi import FastAPI

from aura.api.router import api_router

app = FastAPI(
    title="Aura API",
    description="Aura API is a RESTful API that provides access to the Aura platform. It allows users to interact with the platform's features and functionalities programmatically.",
    version="1.0.0",
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "Welcome to the Aura API!"}


@app.get("/health")
def health_check():
    return {
        "status": "UP"
    }
