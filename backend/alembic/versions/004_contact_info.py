"""add contact-info columns to startupindia_companies

Revision ID: 004
Revises: 003
Create Date: 2026-06-06 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("startupindia_companies", sa.Column("contact_email", sa.String(255), nullable=True))
    op.add_column("startupindia_companies", sa.Column("contact_phone", sa.String(50), nullable=True))
    op.add_column("startupindia_companies", sa.Column("contact_address", sa.Text, nullable=True))
    op.add_column("startupindia_companies", sa.Column("linkedin_url", sa.String(500), nullable=True))
    op.add_column("startupindia_companies", sa.Column("twitter_url", sa.String(500), nullable=True))
    op.add_column("startupindia_companies", sa.Column("facebook_url", sa.String(500), nullable=True))
    op.add_column("startupindia_companies", sa.Column("source_url", sa.String(500), nullable=True))
    op.add_column("startupindia_companies", sa.Column("contact_enriched_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for col in ("contact_email", "contact_phone", "contact_address", "linkedin_url",
                "twitter_url", "facebook_url", "source_url", "contact_enriched_at"):
        op.drop_column("startupindia_companies", col)
