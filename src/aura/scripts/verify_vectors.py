"""Read-only smoke check after seeding: local MiniLM → persisted vector → retrieval."""

import asyncio

from sqlalchemy import func, select

from aura.db.models import TaxRuleChunk
from aura.db.session import AsyncSessionFactory, close_database
from aura.services import embeddings


async def verify():
    try:
        async with AsyncSessionFactory() as session:
            count = await session.scalar(
                select(func.count())
                .select_from(TaxRuleChunk)
                .where(TaxRuleChunk.embedding.is_not(None))
            )
            if not count:
                raise RuntimeError("No stored embeddings. Seed or reindex first.")
            vector = (await embeddings.embed(["rebate"]))[0]
            nearest = await session.scalar(
                select(TaxRuleChunk.id)
                .where(TaxRuleChunk.embedding_model == embeddings.MODEL_ID)
                .order_by(TaxRuleChunk.embedding.cosine_distance(vector))
                .limit(1)
            )
            if nearest is None:
                raise RuntimeError("Vector retrieval returned no rules")
            print(f"Verified {count} embedded rule chunks and database retrieval")
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(verify())
