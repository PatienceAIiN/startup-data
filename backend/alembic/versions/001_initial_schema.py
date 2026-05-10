"""initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_admin', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True)),
        sa.Column('last_login', sa.DateTime(timezone=True)),
        sa.Column('login_count', sa.Integer, default=0),
    )
    op.create_index('idx_users_email', 'users', ['email'])

    op.create_table(
        'zauba_companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('cin', sa.String(50), unique=True),
        sa.Column('company_name', sa.String(500), nullable=False),
        sa.Column('company_status', sa.String(100)),
        sa.Column('roc_code', sa.String(50)),
        sa.Column('registration_number', sa.String(100)),
        sa.Column('company_category', sa.String(200)),
        sa.Column('company_subcategory', sa.String(200)),
        sa.Column('class_of_company', sa.String(100)),
        sa.Column('date_of_incorporation', sa.Date),
        sa.Column('authorised_capital', sa.BigInteger),
        sa.Column('paid_up_capital', sa.BigInteger),
        sa.Column('registered_address', sa.Text),
        sa.Column('listing_status', sa.String(100)),
        sa.Column('scraped_at', sa.DateTime(timezone=True)),
        sa.Column('scrape_job_id', postgresql.UUID(as_uuid=True)),
    )
    op.create_index('idx_zauba_cin', 'zauba_companies', ['cin'])
    op.create_index('idx_zauba_incorporation', 'zauba_companies', ['date_of_incorporation'])

    op.create_table(
        'datagov_companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('cin', sa.String(50)),
        sa.Column('company_name', sa.String(500), nullable=False),
        sa.Column('company_status', sa.String(100)),
        sa.Column('roc_code', sa.String(50)),
        sa.Column('registration_number', sa.String(100)),
        sa.Column('company_category', sa.String(200)),
        sa.Column('date_of_incorporation', sa.Date),
        sa.Column('state', sa.String(100)),
        sa.Column('raw_data', postgresql.JSONB),
        sa.Column('scraped_at', sa.DateTime(timezone=True)),
        sa.Column('scrape_job_id', postgresql.UUID(as_uuid=True)),
    )
    op.create_index('idx_datagov_cin', 'datagov_companies', ['cin'])

    op.create_table(
        'matched_companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('zauba_id', postgresql.UUID(as_uuid=True)),
        sa.Column('datagov_id', postgresql.UUID(as_uuid=True)),
        sa.Column('company_name', sa.String(500), nullable=False),
        sa.Column('cin', sa.String(50)),
        sa.Column('match_score', sa.Float, nullable=False),
        sa.Column('match_method', sa.String(50)),
        sa.Column('company_status', sa.String(100)),
        sa.Column('roc_code', sa.String(50)),
        sa.Column('company_category', sa.String(200)),
        sa.Column('date_of_incorporation', sa.Date),
        sa.Column('state', sa.String(100)),
        sa.Column('authorised_capital', sa.BigInteger),
        sa.Column('paid_up_capital', sa.BigInteger),
        sa.Column('registered_address', sa.Text),
        sa.Column('is_startup', sa.Boolean, default=False),
        sa.Column('incorporation_year', sa.Integer),
        sa.Column('created_at', sa.DateTime(timezone=True)),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )
    op.create_index('idx_matched_cin', 'matched_companies', ['cin'])
    op.create_index('idx_matched_incorporation', 'matched_companies', ['date_of_incorporation'])
    op.create_index('idx_matched_score', 'matched_companies', ['match_score'])
    op.create_index('idx_matched_state', 'matched_companies', ['state'])

    op.create_table(
        'scrape_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('triggered_by', postgresql.UUID(as_uuid=True)),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('source', sa.String(50)),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('records_scraped', sa.Integer, default=0),
        sa.Column('records_matched', sa.Integer, default=0),
        sa.Column('error_message', sa.Text),
        sa.Column('job_metadata', postgresql.JSONB),
    )

    op.create_table(
        'export_files',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('exported_by', postgresql.UUID(as_uuid=True)),
        sa.Column('file_type', sa.String(10)),
        sa.Column('file_name', sa.String(500)),
        sa.Column('r2_key', sa.String(500)),
        sa.Column('r2_url', sa.Text),
        sa.Column('file_size_bytes', sa.BigInteger),
        sa.Column('record_count', sa.Integer),
        sa.Column('filter_params', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True)),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
    )

    op.create_table(
        'rate_limit_log',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('endpoint', sa.String(200)),
        sa.Column('hit_at', sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table('rate_limit_log')
    op.drop_table('export_files')
    op.drop_table('scrape_jobs')
    op.drop_table('matched_companies')
    op.drop_table('datagov_companies')
    op.drop_table('zauba_companies')
    op.drop_table('users')
