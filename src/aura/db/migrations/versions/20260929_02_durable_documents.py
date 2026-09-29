"""Persist upload bytes and safe processing failures across restarts."""

from alembic import op

revision = "20260929_02"
down_revision = "20260902_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE tax_rule_chunks DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding")
    # IF NOT EXISTS supports fresh installs: the initial migration uses metadata.
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_content BYTEA")
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_error VARCHAR(255)")
    op.execute(
        "UPDATE documents SET processing_status = 'QUEUED' WHERE processing_status = 'PROCESSING'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_queue ON documents (created_at) WHERE processing_status = 'QUEUED'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_documents_queue")
    op.drop_column("documents", "processing_error")
    op.drop_column("documents", "file_content")
