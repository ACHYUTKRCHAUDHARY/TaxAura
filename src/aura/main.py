from fastapi import FastAPI

app=FastAPI(
    title="Aura API",
    description="Aura API is a RESTful API that provides access to the Aura platform. It allows users to interact with the platform's features and functionalities programmatically.",
    version="1.0.0",
)

@app.get("/")
def root():
    return {"message": "Welcome to the Aura API!"}


@app.get("/health")
def health_check():
    return {
        "status": "UP"
    }
