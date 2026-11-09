"""Add direct Page-scoped FIFO video analysis queue."""
from alembic import op
import sqlalchemy as sa

revision = "0008_reference_video_queue"
down_revision = "0007_reference_creative_insights"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reference_videos", sa.Column("page_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_reference_videos_page_id_pages", "reference_videos", "pages",
        ["page_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index("ix_reference_videos_page_id", "reference_videos", ["page_id"])
    op.create_index("ix_reference_videos_owner_page", "reference_videos", ["owner_id", "page_id"])
    op.add_column("reference_videos", sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("reference_videos", "reference_page_id", existing_type=sa.Integer(), nullable=True)
    op.execute("""
        UPDATE reference_videos AS rv
        SET page_id = rp.page_id
        FROM reference_pages AS rp
        WHERE rv.reference_page_id = rp.id AND rv.page_id IS NULL
    """)

    op.create_table(
        "reference_video_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("page_id", sa.Integer(), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=False),
        sa.Column("title", sa.String(200), nullable=False, server_default="Reference video"),
        sa.Column("views_count", sa.Integer()),
        sa.Column("reactions_count", sa.Integer()),
        sa.Column("shares_count", sa.Integer()),
        sa.Column("comments_count", sa.Integer()),
        sa.Column("manual_comments", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("engagement_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(30), nullable=False, server_default="queued"),
        sa.Column("queue_position", sa.Integer()),
        sa.Column("reference_video_id", sa.Integer(), sa.ForeignKey("reference_videos.id", ondelete="SET NULL")),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_reference_video_jobs_owner_id", "reference_video_jobs", ["owner_id"])
    op.create_index("ix_reference_video_jobs_page_id", "reference_video_jobs", ["page_id"])
    op.create_index("ix_reference_video_jobs_fifo", "reference_video_jobs", ["status", "created_at", "id"])
    op.create_index("ix_reference_video_jobs_owner_page", "reference_video_jobs", ["owner_id", "page_id"])


def downgrade() -> None:
    op.drop_table("reference_video_jobs")
    op.drop_index("ix_reference_videos_owner_page", table_name="reference_videos")
    op.drop_index("ix_reference_videos_page_id", table_name="reference_videos")
    op.drop_column("reference_videos", "analyzed_at")
    op.drop_constraint("fk_reference_videos_page_id_pages", "reference_videos", type_="foreignkey")
    op.drop_column("reference_videos", "page_id")
    op.alter_column("reference_videos", "reference_page_id", existing_type=sa.Integer(), nullable=False)
