"""add website column to matched_companies

Revision ID: 003
Revises: 002
Create Date: 2026-06-05 16:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("matched_companies", sa.Column("website", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("matched_companies", "website")
