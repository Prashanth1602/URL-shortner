"""
Initial migration: create url_mappings table.

Revision ID: 0001_create_url_mappings
Revises: 
Create Date: 2025-10-03
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_create_url_mappings'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'url_mappings',
        sa.Column('short_code', sa.String(length=10), primary_key=True),
        sa.Column('original_link', sa.String(length=2048), nullable=False),
        sa.Column('request_count', sa.Integer(), nullable=False, server_default='0')
    )
    # Optional: explicit index (PK already indexed). Uncomment if needed.
    # op.create_index('ix_url_mappings_short_code', 'url_mappings', ['short_code'], unique=True)


def downgrade():
    op.drop_table('url_mappings')
