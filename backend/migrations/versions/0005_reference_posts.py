"""Add reference post collection and metric snapshots for R2."""
from alembic import op
import sqlalchemy as sa

revision = "0005_reference_posts"
down_revision = "0004_reference_pages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reference_posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("reference_page_id", sa.Integer(), sa.ForeignKey("reference_pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_post_id", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("permalink_url", sa.String(2048)),
        sa.Column("media_type", sa.String(40)),
        sa.Column("created_time", sa.DateTime(timezone=True)),
        sa.Column("source_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("reference_page_id", "external_post_id", name="uq_reference_post_external"),
    )
    op.create_index("ix_reference_posts_owner_id", "reference_posts", ["owner_id"])
    op.create_index("ix_reference_posts_reference_page_id", "reference_posts", ["reference_page_id"])
    op.create_index("ix_reference_posts_owner_reference_created", "reference_posts", ["owner_id", "reference_page_id", "created_time"])
    op.create_table(
        "reference_post_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("reference_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reactions_count", sa.Integer()),
        sa.Column("comments_count", sa.Integer()),
        sa.Column("shares_count", sa.Integer()),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("available_fields", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.create_index("ix_reference_post_metrics_owner_id", "reference_post_metrics", ["owner_id"])
    op.create_index("ix_reference_post_metrics_post_id", "reference_post_metrics", ["post_id"])
    op.create_index("ix_reference_post_metrics_post_captured", "reference_post_metrics", ["post_id", "captured_at"])


def downgrade() -> None:
    op.drop_table("reference_post_metrics")
    op.drop_table("reference_posts")
