"""Remove engagement notes from reference video records.

The original migrations are intentionally left immutable. This migration drops
the obsolete notes columns from both stored videos and queued jobs.
"""
from alembic import op

revision = "0010_remove_engagement_notes"
down_revision = "0009_creative_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("reference_video_jobs", "engagement_notes")
    op.drop_column("reference_videos", "engagement_notes")


def downgrade() -> None:
    import sqlalchemy as sa

    op.add_column(
        "reference_videos",
        sa.Column("engagement_notes", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "reference_video_jobs",
        sa.Column("engagement_notes", sa.Text(), nullable=False, server_default=""),
    )
