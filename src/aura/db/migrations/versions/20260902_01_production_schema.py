"""Create production TaxAura schema."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


def baseline_metadata():
    """Historical schema only; never import application models in migrations."""
    metadata = sa.MetaData()

    def identity():
        return sa.Column("id", UUID(as_uuid=True), primary_key=True)

    def created():
        return sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        )

    sa.Table(
        "users",
        metadata,
        identity(),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        created(),
    )
    documents = sa.Table(
        "documents",
        metadata,
        identity(),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("extracted_text", sa.Text()),
        sa.Column("processing_status", sa.String(30), nullable=False),
        created(),
    )
    sa.Index("idx_documents_user_created_at", documents.c.user_id, documents.c.created_at.desc())
    sa.Table(
        "tax_rule_chunks",
        metadata,
        identity(),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("source_url", sa.String(1000)),
        sa.Column("content", sa.Text(), nullable=False),
        created(),
    )
    sa.Table(
        "document_chunks",
        metadata,
        identity(),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        created(),
    )
    return metadata


revision = "20260902_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    baseline_metadata().create_all(bind=op.get_bind(), checkfirst=True)
    # Harden databases created by the earlier MVP SQL script. Legacy accounts
    # are disabled until an administrator assigns a real password.
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'USER'")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")
    op.execute(
        "UPDATE users SET password_hash = 'legacy-account-reset-required', is_active = FALSE WHERE password_hash IS NULL"
    )
    op.execute("ALTER TABLE users ALTER COLUMN password_hash SET NOT NULL")
    op.execute("ALTER TABLE users ALTER COLUMN role SET NOT NULL")
    op.execute("ALTER TABLE users ALTER COLUMN is_active SET NOT NULL")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_checksum_hash ON documents USING HASH(checksum)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_extracted_text_fts ON documents USING GIN (to_tsvector('english', coalesce(extracted_text, '')))"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_tax_rule_chunks_fts ON tax_rule_chunks USING GIN (to_tsvector('english', content))"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_document_chunks_fts ON document_chunks USING GIN (to_tsvector('english', content))"
    )


def downgrade() -> None:
    baseline_metadata().drop_all(bind=op.get_bind(), checkfirst=True)
