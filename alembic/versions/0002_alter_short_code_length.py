"""
Alter short_code length to 64 to accommodate Base62(SHA-256).

Revision ID: 0002_alter_short_code_length
Revises: 0001_create_url_mappings
Create Date: 2025-10-03
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_alter_short_code_length'
down_revision = '0001_create_url_mappings'
branch_labels = None
depends_on = None

def upgrade():
    op.alter_column(
        'url_mappings',
        'short_code',
        existing_type=sa.String(length=10),
        type_=sa.String(length=64),
        existing_nullable=False
    )


def downgrade():
    op.alter_column(
        'url_mappings',
        'short_code',
        existing_type=sa.String(length=64),
        type_=sa.String(length=10),
        existing_nullable=False
    )
