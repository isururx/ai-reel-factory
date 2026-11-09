"""Store Page-specific creative insights extracted from reference videos."""
from alembic import op
import sqlalchemy as sa

revision = "0007_reference_creative_insights"
down_revision = "0006_reference_videos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reference_creative_insights",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("page_id", sa.Integer(), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reference_video_id", sa.Integer(), sa.ForeignKey("reference_videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("insight_type", sa.String(60), nullable=False, server_default="creative_analysis"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("review_status", sa.String(30), nullable=False, server_default="pending_review"),
        sa.Column("reviewer_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_reference_creative_insights_owner_id", "reference_creative_insights", ["owner_id"])
    op.create_index("ix_reference_creative_insights_page_id", "reference_creative_insights", ["page_id"])
    op.create_index("ix_reference_creative_insights_reference_video_id", "reference_creative_insights", ["reference_video_id"])
    op.create_index("ix_reference_insights_owner_page_status", "reference_creative_insights", ["owner_id", "page_id", "review_status"])


def downgrade() -> None:
    op.drop_table("reference_creative_insights")
