"""Add reference video ingestion and manually supplied engagement context."""
from alembic import op
import sqlalchemy as sa

revision = "0006_reference_videos"
down_revision = "0005_reference_posts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reference_videos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("reference_page_id", sa.Integer(), sa.ForeignKey("reference_pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reference_post_id", sa.Integer(), sa.ForeignKey("reference_posts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(200), nullable=False, server_default="Reference video"),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("object_key", sa.String(1024), nullable=False, unique=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("views_count", sa.Integer()),
        sa.Column("reactions_count", sa.Integer()),
        sa.Column("shares_count", sa.Integer()),
        sa.Column("comments_count", sa.Integer()),
        sa.Column("manual_comments", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("engagement_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("analysis_status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("analysis_result", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_reference_videos_owner_id", "reference_videos", ["owner_id"])
    op.create_index("ix_reference_videos_reference_page_id", "reference_videos", ["reference_page_id"])
    op.create_index("ix_reference_videos_reference_post_id", "reference_videos", ["reference_post_id"])
    op.create_index("ix_reference_videos_owner_reference", "reference_videos", ["owner_id", "reference_page_id"])


def downgrade() -> None:
    op.drop_table("reference_videos")
