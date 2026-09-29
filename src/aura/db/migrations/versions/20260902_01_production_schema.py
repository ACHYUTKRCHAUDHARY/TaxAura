"""Create production TaxAura schema."""

from alembic import op

from aura.db.models import Base

revision = "20260902_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)
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
    Base.metadata.drop_all(bind=op.get_bind(), checkfirst=True)
