"""Add favorite column to favorite_products table

Revision ID: add_favorite_bool_col
Revises: 06182fd48224
Create Date: 2026-04-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_favorite_bool_col'
down_revision = '06182fd48224'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add favorite column with default value True
    op.add_column('favorite_products', 
                  sa.Column('favorite', sa.Boolean(), nullable=False, server_default='1'))


def downgrade() -> None:
    # Remove favorite column
    op.drop_column('favorite_products', 'favorite')