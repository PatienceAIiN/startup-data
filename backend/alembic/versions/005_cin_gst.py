"""add cin_real and gst columns to startupindia_companies

Revision ID: 005
Revises: 004
Create Date: 2026-06-06 02:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("startupindia_companies", sa.Column("cin_real", sa.String(50), nullable=True))
    op.add_column("startupindia_companies", sa.Column("gst", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("startupindia_companies", "gst")
    op.drop_column("startupindia_companies", "cin_real")
