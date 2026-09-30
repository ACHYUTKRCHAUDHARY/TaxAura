"""Keep relational chunks and semantic embeddings in the same database.

Existing chunk content is retained. Run aura.scripts.reindex after upgrading.
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "20261001_03"
down_revision = "20260929_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    for table in ("tax_rule_chunks", "document_chunks"):
        op.add_column(table, sa.Column("embedding", Vector(384), nullable=True))
        op.add_column(table, sa.Column("embedding_model", sa.String(100), nullable=True))
        op.create_index(
            f"idx_{table}_embedding",
            table,
            ["embedding"],
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        )
    op.add_column("document_chunks", sa.Column("chunk_index", sa.Integer(), nullable=True))
    # Legacy chunks have no ordering field; preserve every row and assign a stable position.
    op.execute("""
        WITH positions AS (
            SELECT id, row_number() OVER (PARTITION BY document_id ORDER BY created_at, id) - 1 AS position
            FROM document_chunks
        )
        UPDATE document_chunks SET chunk_index = positions.position
        FROM positions WHERE document_chunks.id = positions.id
    """)
    op.alter_column("document_chunks", "chunk_index", nullable=False)
    op.create_unique_constraint(
        "uq_document_chunk_position", "document_chunks", ["document_id", "chunk_index"]
    )
    op.create_check_constraint("ck_document_chunk_position", "document_chunks", "chunk_index >= 0")
    op.create_index(
        "idx_document_chunks_user_document", "document_chunks", ["user_id", "document_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_document_chunks_user_document", table_name="document_chunks")
    op.drop_constraint("ck_document_chunk_position", "document_chunks", type_="check")
    op.drop_constraint("uq_document_chunk_position", "document_chunks", type_="unique")
    op.drop_column("document_chunks", "chunk_index")
    for table in ("document_chunks", "tax_rule_chunks"):
        op.drop_index(f"idx_{table}_embedding", table_name=table)
        op.drop_column(table, "embedding_model")
        op.drop_column(table, "embedding")
    # The extension may be used by other applications; never drop it implicitly.
