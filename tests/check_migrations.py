"""CI-only: fresh install, legacy content upgrade, downgrade, and re-upgrade.

Requires a NEW DISPOSABLE database. Refuses a database with existing user tables.
"""

import asyncio
import os
import subprocess
import sys
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

URL = os.environ["TEST_DATABASE_URL"]
OWNER, DOC, CHUNK, RULE = [uuid4() for _ in range(4)]


def migrate(target, direction="upgrade"):
    subprocess.run(
        [sys.executable, "-m", "alembic", direction, target],
        check=True,
        env={**os.environ, "DATABASE_URL": URL},
    )


async def check_empty():
    engine = create_async_engine(URL)
    try:
        async with engine.connect() as session:
            assert await session.scalar(text("SELECT to_regclass('public.users')")) is None, (
                "Use an empty disposable database"
            )
    finally:
        await engine.dispose()


async def seed_legacy():
    engine = create_async_engine(URL)
    try:
        async with engine.begin() as session:
            await session.execute(
                text(
                    "INSERT INTO users(id,email,full_name,password_hash,role,is_active) VALUES(:id,'migration@example.com','Migration','unused','USER',true)"
                ),
                {"id": OWNER},
            )
            await session.execute(
                text(
                    "INSERT INTO documents(id,user_id,filename,mime_type,storage_path,checksum,processing_status,file_content) VALUES(:id,:owner,'old.pdf','application/pdf','database','test','COMPLETED',:body)"
                ),
                {"id": DOC, "owner": OWNER, "body": b"existing upload"},
            )
            await session.execute(
                text(
                    "INSERT INTO document_chunks(id,document_id,user_id,content) VALUES(:id,:doc,:owner,'Existing private salary text')"
                ),
                {"id": CHUNK, "doc": DOC, "owner": OWNER},
            )
            await session.execute(
                text(
                    "INSERT INTO tax_rule_chunks(id,source_name,content) VALUES(:id,'Migration source','Existing rule text')"
                ),
                {"id": RULE},
            )
    finally:
        await engine.dispose()


async def verify_and_cleanup(cleanup=False):
    engine = create_async_engine(URL)
    try:
        async with engine.begin() as session:
            row = (
                await session.execute(
                    text("SELECT content,chunk_index,embedding FROM document_chunks WHERE id=:id"),
                    {"id": CHUNK},
                )
            ).one()
            assert (
                row.content == "Existing private salary text"
                and row.chunk_index == 0
                and row.embedding is None
            )
            assert (
                await session.scalar(
                    text("SELECT file_content FROM documents WHERE id=:id"), {"id": DOC}
                )
                == b"existing upload"
            )
            assert (
                await session.scalar(
                    text("SELECT content FROM tax_rule_chunks WHERE id=:id"), {"id": RULE}
                )
                == "Existing rule text"
            )
            indexes = list(
                await session.scalars(
                    text("SELECT indexname FROM pg_indexes WHERE indexdef LIKE '%USING hnsw%'")
                )
            )
            assert len(indexes) == 2
            if cleanup:
                await session.execute(text("DELETE FROM documents WHERE id=:id"), {"id": DOC})
                await session.execute(text("DELETE FROM users WHERE id=:id"), {"id": OWNER})
                await session.execute(
                    text("DELETE FROM tax_rule_chunks WHERE id=:id"), {"id": RULE}
                )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_empty())
    migrate("head")  # Fresh installation proves historical migrations are stable.
    migrate("20260929_02", "downgrade")
    asyncio.run(seed_legacy())
    migrate("head")
    asyncio.run(verify_and_cleanup())
    migrate("20260929_02", "downgrade")
    migrate("head")
    asyncio.run(verify_and_cleanup(cleanup=True))
    print("Fresh install, legacy content preservation, downgrade and re-upgrade passed")
