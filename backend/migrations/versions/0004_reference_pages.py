"""Add reference Page registry for R1."""

from alembic import op
import sqlalchemy as sa

revision = "0004_reference_pages"
down_revision = "0003_trend_discovery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reference_pages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("page_id", sa.Integer(), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(length=30), nullable=False, server_default="facebook"),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("normalized_url", sa.String(length=2048), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("owner_id", "page_id", "normalized_url", name="uq_reference_owner_page_url"),
    )
    op.create_index("ix_reference_pages_owner_id", "reference_pages", ["owner_id"])
    op.create_index("ix_reference_pages_page_id", "reference_pages", ["page_id"])
    op.create_index("ix_reference_owner_page_status", "reference_pages", ["owner_id", "page_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_reference_owner_page_status", table_name="reference_pages")
    op.drop_index("ix_reference_pages_page_id", table_name="reference_pages")
    op.drop_index("ix_reference_pages_owner_id", table_name="reference_pages")
    op.drop_table("reference_pages")
