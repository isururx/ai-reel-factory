"""Persist provider/model attempts for reference video analysis."""
from alembic import op
import sqlalchemy as sa

revision = "0010_analysis_model_attempts"
down_revision = "0009_creative_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reference_videos", sa.Column("analysis_provider", sa.String(40), nullable=True))
    op.add_column("reference_videos", sa.Column("analysis_model", sa.String(160), nullable=True))
    op.add_column("reference_videos", sa.Column("analysis_attempt_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("reference_videos", sa.Column("analysis_total_duration_ms", sa.Integer(), nullable=True))
    op.add_column("reference_video_jobs", sa.Column("analysis_primary_provider", sa.String(40), nullable=True))
    op.add_column("reference_video_jobs", sa.Column("analysis_primary_model", sa.String(160), nullable=True))
    op.create_table(
        "reference_video_analysis_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("page_id", sa.Integer(), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reference_video_id", sa.Integer(), sa.ForeignKey("reference_videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("reference_video_jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("model_id", sa.String(160), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_code", sa.String(100)),
        sa.Column("error_message", sa.Text()),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    for column in ("owner_id", "page_id", "reference_video_id", "job_id"):
        op.create_index(f"ix_reference_video_analysis_attempts_{column}", "reference_video_analysis_attempts", [column])


def downgrade() -> None:
    op.drop_table("reference_video_analysis_attempts")
    op.drop_column("reference_videos", "analysis_total_duration_ms")
    op.drop_column("reference_videos", "analysis_attempt_count")
    op.drop_column("reference_videos", "analysis_model")
    op.drop_column("reference_video_jobs", "analysis_primary_model")
    op.drop_column("reference_video_jobs", "analysis_primary_provider")
    op.drop_column("reference_videos", "analysis_provider")
