"""add dipp_number column

Revision ID: 006
Revises: 005
Create Date: 2026-06-06 03:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("startupindia_companies", sa.Column("dipp_number", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("startupindia_companies", "dipp_number")
