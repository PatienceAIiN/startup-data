"""startupindia companies + scrape cursor

Revision ID: 002
Revises: 001
Create Date: 2026-06-05 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "startupindia_companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id", sa.String(100), nullable=False, unique=True),
        sa.Column("profile_url", sa.String(500)),
        sa.Column("company_name", sa.String(500), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("industry", sa.String(200)),
        sa.Column("sector", sa.String(200)),
        sa.Column("stage", sa.String(100)),
        sa.Column("state", sa.String(100)),
        sa.Column("city", sa.String(100)),
        sa.Column("website", sa.String(500)),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("badges", postgresql.JSONB),
        sa.Column("dpiit_recognised", sa.Boolean, server_default=sa.text("false")),
        sa.Column("raw", postgresql.JSONB),
        sa.Column("scraped_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_startupindia_profile_id", "startupindia_companies", ["profile_id"], unique=True)
    op.create_index("idx_startupindia_name", "startupindia_companies", ["company_name"])
    op.create_index("idx_startupindia_industry", "startupindia_companies", ["industry"])
    op.create_index("idx_startupindia_sector", "startupindia_companies", ["sector"])
    op.create_index("idx_startupindia_stage", "startupindia_companies", ["stage"])
    op.create_index("idx_startupindia_state", "startupindia_companies", ["state"])

    op.create_table(
        "scrape_cursors",
        sa.Column("source", sa.String(50), primary_key=True),
        sa.Column("page", sa.Integer, server_default="0"),
        sa.Column("exhausted", sa.Boolean, server_default=sa.text("false")),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_count", sa.Integer, server_default="0"),
        sa.Column("notes", sa.String(500)),
    )


def downgrade() -> None:
    op.drop_table("scrape_cursors")
    op.drop_index("idx_startupindia_state", table_name="startupindia_companies")
    op.drop_index("idx_startupindia_stage", table_name="startupindia_companies")
    op.drop_index("idx_startupindia_sector", table_name="startupindia_companies")
    op.drop_index("idx_startupindia_industry", table_name="startupindia_companies")
    op.drop_index("idx_startupindia_name", table_name="startupindia_companies")
    op.drop_index("idx_startupindia_profile_id", table_name="startupindia_companies")
    op.drop_table("startupindia_companies")
