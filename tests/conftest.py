import os

os.environ.setdefault("DOCUMENT_WORKER_ENABLED", "false")
os.environ.setdefault("CHROMA_MODE", "disabled")
os.environ.setdefault("AI_MODE", "extractive")
