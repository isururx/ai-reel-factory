"""Store timestamped creative elements and reusable Page patterns."""
from alembic import op
import sqlalchemy as sa

revision = "0009_creative_intelligence"
down_revision = "0008_reference_video_queue"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "creative_elements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("page_id", sa.Integer(), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reference_video_id", sa.Integer(), sa.ForeignKey("reference_videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("element_type", sa.String(40), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("start_seconds", sa.Float()),
        sa.Column("end_seconds", sa.Float()),
        sa.Column("observed_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("reusable_construction", sa.Text(), nullable=False, server_default=""),
        sa.Column("attributes", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("confidence_score", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_creative_elements_owner_id", "creative_elements", ["owner_id"])
    op.create_index("ix_creative_elements_page_id", "creative_elements", ["page_id"])
    op.create_index("ix_creative_elements_reference_video_id", "creative_elements", ["reference_video_id"])
    op.create_index("ix_creative_elements_page_video", "creative_elements", ["owner_id", "page_id", "reference_video_id"])
    op.create_index("ix_creative_elements_type", "creative_elements", ["owner_id", "page_id", "element_type"])

    op.create_table(
        "creative_patterns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("page_id", sa.Integer(), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("normalized_key", sa.String(220), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("reusable_construction", sa.Text(), nullable=False, server_default=""),
        sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("supporting_video_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Float()),
        sa.Column("status", sa.String(20), nullable=False, server_default="emerging"),
        sa.Column("last_observed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("owner_id", "page_id", "normalized_key", name="uq_creative_pattern_page_key"),
    )
    op.create_index("ix_creative_patterns_owner_id", "creative_patterns", ["owner_id"])
    op.create_index("ix_creative_patterns_page_id", "creative_patterns", ["page_id"])
    op.create_index("ix_creative_patterns_page_status", "creative_patterns", ["owner_id", "page_id", "status"])
    op.create_index("ix_creative_patterns_page_category", "creative_patterns", ["owner_id", "page_id", "category"])

    op.create_table(
        "pattern_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pattern_id", sa.Integer(), sa.ForeignKey("creative_patterns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("creative_element_id", sa.Integer(), sa.ForeignKey("creative_elements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reference_video_id", sa.Integer(), sa.ForeignKey("reference_videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("timestamp_start", sa.Float()),
        sa.Column("timestamp_end", sa.Float()),
        sa.Column("performance_context", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("pattern_id", "creative_element_id", name="uq_pattern_evidence_element"),
    )
    op.create_index("ix_pattern_evidence_pattern_id", "pattern_evidence", ["pattern_id"])
    op.create_index("ix_pattern_evidence_video", "pattern_evidence", ["reference_video_id"])


def downgrade() -> None:
    op.drop_table("pattern_evidence")
    op.drop_table("creative_patterns")
    op.drop_table("creative_elements")
