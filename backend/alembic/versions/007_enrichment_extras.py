"""add enrichment_extras JSONB to startupindia_companies

Revision ID: 007
Revises: 006
Create Date: 2026-06-06 04:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("startupindia_companies", sa.Column("extras", postgresql.JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("startupindia_companies", "extras")
