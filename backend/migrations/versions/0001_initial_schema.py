"""Initial Page, profile, strategy and script schema."""
from alembic import op
import sqlalchemy as sa
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("pages", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("platform", sa.String(30), nullable=False), sa.Column("external_page_id", sa.String(128)), sa.Column("is_active", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.UniqueConstraint("external_page_id", name="uq_pages_external_page_id"))
    op.create_table("page_profiles", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("page_id", sa.Integer(), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False), sa.Column("niche", sa.String(120), nullable=False), sa.Column("target_audience", sa.String(500), nullable=False), sa.Column("language", sa.String(40), nullable=False), sa.Column("tone", sa.JSON(), nullable=False), sa.Column("preferred_formats", sa.JSON(), nullable=False), sa.Column("restricted_topics", sa.JSON(), nullable=False), sa.Column("fact_check_level", sa.String(30), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.UniqueConstraint("page_id", name="uq_page_profiles_page_id"))
    op.create_table("page_strategies", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("page_id", sa.Integer(), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(120), nullable=False), sa.Column("description", sa.String(1000), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("strategy_versions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("strategy_id", sa.Integer(), sa.ForeignKey("page_strategies.id", ondelete="CASCADE"), nullable=False), sa.Column("version_number", sa.Integer(), nullable=False), sa.Column("configuration", sa.JSON(), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.UniqueConstraint("strategy_id", "version_number", name="uq_strategy_versions_strategy_id"))
    op.create_table("content_scripts", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("page_id", sa.Integer(), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False), sa.Column("title", sa.String(200), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("script_versions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("script_id", sa.Integer(), sa.ForeignKey("content_scripts.id", ondelete="CASCADE"), nullable=False), sa.Column("version_number", sa.Integer(), nullable=False), sa.Column("hook", sa.String(500), nullable=False), sa.Column("narration", sa.Text(), nullable=False), sa.Column("caption", sa.Text(), nullable=False), sa.Column("hashtags", sa.JSON(), nullable=False), sa.Column("script_data", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("approval_events", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("script_version_id", sa.Integer(), sa.ForeignKey("script_versions.id", ondelete="CASCADE"), nullable=False), sa.Column("decision", sa.String(20), nullable=False), sa.Column("reviewer", sa.String(120), nullable=False), sa.Column("comments", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    for table, col in [("page_profiles","page_id"),("page_strategies","page_id"),("content_scripts","page_id"),("strategy_versions","strategy_id"),("script_versions","script_id"),("approval_events","script_version_id")]:
        op.create_index(f"ix_{table}_{col}", table, [col])

def downgrade() -> None:
    for table in ["approval_events","script_versions","content_scripts","strategy_versions","page_strategies","page_profiles","pages"]:
        op.drop_table(table)
