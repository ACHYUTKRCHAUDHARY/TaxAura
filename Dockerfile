FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /bin/
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-hin && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev
# Warm the default Chroma embedding model once; do not redownload on each request.
ENV HOME=/home/app
RUN mkdir -p /home/app && uv run --no-sync python -c "from chromadb.utils.embedding_functions import DefaultEmbeddingFunction; DefaultEmbeddingFunction()(['TaxAura model warmup'])"
COPY alembic.ini ./
COPY scripts ./scripts
RUN useradd --create-home --uid 10001 app && chown -R app:app /app /home/app
USER app
EXPOSE 10000
CMD ["sh", "scripts/start.sh"]
