"""Backfill or regenerate pgvector embeddings from stored chunk text, in batches."""

import asyncio
from uuid import UUID

from sqlalchemy import select

from aura.db.models import DocumentChunk, TaxRuleChunk
from aura.db.session import AsyncSessionFactory, close_database
from aura.services.vector_store import index_chunks


async def reindex():
    try:
        for model, kind in ((TaxRuleChunk, "rules"), (DocumentChunk, "documents")):
            count = 0
            last_id: UUID | None = None
            while True:
                # Short, row-locked batches prevent delete/reindex races and unbounded transactions.
                async with AsyncSessionFactory() as session:
                    statement = select(model).order_by(model.id).limit(32).with_for_update()
                    if last_id is not None:
                        statement = statement.where(model.id > last_id)
                    batch = list(await session.scalars(statement))
                    if not batch:
                        break
                    if not await index_chunks(batch):
                        raise RuntimeError(f"Could not embed {kind}; check the local model cache")
                    last_id = batch[-1].id
                    await session.commit()
                    count += len(batch)
            print(f"Indexed {count} {kind} chunks")
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(reindex())
