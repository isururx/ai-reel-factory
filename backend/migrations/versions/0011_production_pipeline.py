"""Add durable script batches, video jobs and Page publishing schedules."""
from alembic import op
import sqlalchemy as sa

revision = "0011_production_pipeline"
down_revision = "0010_analysis_model_attempts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "script_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("page_id", sa.Integer(), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("strategy_id", sa.Integer(), sa.ForeignKey("page_strategies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("strategy_version_id", sa.Integer(), sa.ForeignKey("strategy_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="queued"),
        sa.Column("requested_count", sa.Integer(), nullable=False),
        sa.Column("completed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text()),
    )
    for col in ("owner_id", "page_id", "status"):
        op.create_index(f"ix_script_batches_{col}", "script_batches", [col])

    op.create_table(
        "video_production_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("page_id", sa.Integer(), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("script_id", sa.Integer(), sa.ForeignKey("content_scripts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("script_version_id", sa.Integer(), sa.ForeignKey("script_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="queued"),
        sa.Column("provider", sa.String(40), nullable=False, server_default="vast_ltx"),
        sa.Column("provider_job_id", sa.String(200)),
        sa.Column("request_snapshot", sa.JSON(), nullable=False),
        sa.Column("output_object_key", sa.String(500)),
        sa.Column("error_message", sa.Text()),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("script_version_id", name="uq_video_production_jobs_script_version"),
        sa.UniqueConstraint("provider_job_id", name="uq_video_production_jobs_provider_job_id"),
    )
    for col in ("owner_id", "page_id", "script_id", "status"):
        op.create_index(f"ix_video_production_jobs_{col}", "video_production_jobs", [col])

    op.create_table(
        "page_publishing_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("page_id", sa.Integer(), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("daily_reel_limit", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("posting_slots", sa.JSON(), nullable=False),
        sa.Column("minimum_interval_minutes", sa.Integer(), nullable=False, server_default="180"),
        sa.Column("performance_optimisation_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("page_id", name="uq_page_publishing_settings_page_id"),
    )
    op.create_index("ix_page_publishing_settings_owner_id", "page_publishing_settings", ["owner_id"])

    op.create_table(
        "scheduled_publications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("page_id", sa.Integer(), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("video_job_id", sa.Integer(), sa.ForeignKey("video_production_jobs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("script_version_id", sa.Integer(), sa.ForeignKey("script_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="scheduled"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("external_post_id", sa.String(200)),
        sa.Column("result_metadata", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("page_id", "script_version_id", name="uq_publication_page_script_version"),
        sa.UniqueConstraint("video_job_id", name="uq_scheduled_publications_video_job_id"),
        sa.UniqueConstraint("external_post_id", name="uq_scheduled_publications_external_post_id"),
    )
    for col in ("owner_id", "page_id", "status", "scheduled_at"):
        op.create_index(f"ix_scheduled_publications_{col}", "scheduled_publications", [col])


def downgrade() -> None:
    op.drop_table("scheduled_publications")
    op.drop_table("page_publishing_settings")
    op.drop_table("video_production_jobs")
    op.drop_table("script_batches")
