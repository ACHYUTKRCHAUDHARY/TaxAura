"""Local CPU embeddings. Private documents never leave the backend for embedding."""

import asyncio
from functools import lru_cache
from threading import Lock

import numpy as np

from aura.core.config import settings

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
# A pipeline version prevents mixing embeddings after a future model/normalization change.
MODEL_ID = "minilm-l6-v2-fastembed-v1"
DIMENSIONS = 384
_lock = Lock()


@lru_cache(maxsize=1)
def model():
    from fastembed import TextEmbedding

    return TextEmbedding(
        model_name=MODEL_NAME, cache_dir=str(settings.embedding_cache_dir), threads=2
    )


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    # Bound CPU work and initialize only once even when requests arrive concurrently.
    with _lock:
        vectors = np.asarray(list(model().embed(texts, batch_size=32)), dtype=np.float32)
    if vectors.shape != (len(texts), DIMENSIONS) or not np.isfinite(vectors).all():
        raise ValueError("Invalid embedding dimensions or values")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    if (norms == 0).any():
        raise ValueError("Zero embeddings are not searchable with cosine distance")
    return (vectors / norms).tolist()


async def embed(texts: list[str]) -> list[list[float]]:
    return await asyncio.to_thread(embed_texts, texts)


if __name__ == "__main__":
    embed_texts(["TaxAura model warmup"])
