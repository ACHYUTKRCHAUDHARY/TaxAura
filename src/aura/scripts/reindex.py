"""Rebuild Chroma vectors from authoritative PostgreSQL records."""

import asyncio

from sqlalchemy import select

from aura.db.models import DocumentChunk, TaxRuleChunk
from aura.db.session import AsyncSessionFactory, close_database
from aura.services.vector_store import index_chunks


async def reindex():
    try:
        async with AsyncSessionFactory() as session:
            for model, kind in ((TaxRuleChunk, "rules"), (DocumentChunk, "documents")):
                rows = await session.stream_scalars(select(model).execution_options(yield_per=32))
                count = 0
                async for batch in rows.partitions(32):
                    if not await index_chunks(batch, kind):
                        raise RuntimeError(f"Could not index {kind}; check Chroma configuration")
                    count += len(batch)
                print(f"Indexed {count} {kind} chunks")
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(reindex())
