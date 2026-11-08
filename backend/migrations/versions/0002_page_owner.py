"""Add Supabase owner identity to Page workspaces."""

from alembic import op
import sqlalchemy as sa

revision = "0002_page_owner"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pages", sa.Column("owner_id", sa.String(length=36), nullable=True))
    op.create_index("ix_pages_owner_id", "pages", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_pages_owner_id", table_name="pages")
    op.drop_column("pages", "owner_id")
