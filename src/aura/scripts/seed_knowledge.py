"""Idempotently load a small, dated starter source for AY 2026-27."""

import asyncio

from sqlalchemy import select

from aura.db.models import TaxRuleChunk
from aura.db.session import AsyncSessionFactory, close_database
from aura.schemas.rag import TaxRuleIngestRequest
from aura.services.rag_service import ingest_tax_rule

SOURCE = "Income Tax Department — AY 2026-27 salaried individuals"
CONTENT = """Scope: FY 2025-26 / AY 2026-27, resident salaried individuals below age 60, ordinary slab-rate income only. The new-regime slabs are: up to Rs 4 lakh nil; Rs 4–8 lakh 5%; Rs 8–12 lakh 10%; Rs 12–16 lakh 15%; Rs 16–20 lakh 20%; Rs 20–24 lakh 25%; above Rs 24 lakh 30%. Eligible resident individuals with total income up to Rs 12 lakh receive section 87A rebate up to Rs 60,000. Health and education cess is 4% of income tax plus surcharge. This starter summary does not cover special-rate income or all deductions. Use the original source and verify eligibility before filing."""


async def seed():
    try:
        async with AsyncSessionFactory() as session:
            if await session.scalar(
                select(TaxRuleChunk.id).where(TaxRuleChunk.source_name == SOURCE).limit(1)
            ):
                print("Starter knowledge already exists; use reindex to rebuild vectors.")
                return
            count, indexed = await ingest_tax_rule(
                TaxRuleIngestRequest(
                    source_name=SOURCE,
                    source_url="https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1",
                    content=CONTENT,
                ),
                session,
            )
            print(f"Created {count} chunks; Chroma indexed: {indexed}")
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(seed())
