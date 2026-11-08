"""Add RSS trend discovery and page recommendations."""

from alembic import op
import sqlalchemy as sa

revision = "0003_trend_discovery"
down_revision = "0002_page_owner"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trend_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("source_name", sa.String(length=80), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("source_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.UniqueConstraint("owner_id", "source_url", name="uq_trend_owner_source_url"),
    )
    op.create_index("ix_trend_items_owner_id", "trend_items", ["owner_id"])
    op.create_index("ix_trend_owner_collected", "trend_items", ["owner_id", "collected_at"])
    op.create_table(
        "page_trend_recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("page_id", sa.Integer(), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trend_id", sa.Integer(), sa.ForeignKey("trend_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="suggested"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("page_id", "trend_id", name="uq_page_trend_recommendation"),
    )
    op.create_index("ix_page_trend_recommendations_page_id", "page_trend_recommendations", ["page_id"])
    op.create_index("ix_page_trend_status_score", "page_trend_recommendations", ["page_id", "status", "score"])


def downgrade() -> None:
    op.drop_index("ix_page_trend_status_score", table_name="page_trend_recommendations")
    op.drop_index("ix_page_trend_recommendations_page_id", table_name="page_trend_recommendations")
    op.drop_table("page_trend_recommendations")
    op.drop_index("ix_trend_owner_collected", table_name="trend_items")
    op.drop_index("ix_trend_items_owner_id", table_name="trend_items")
    op.drop_table("trend_items")
