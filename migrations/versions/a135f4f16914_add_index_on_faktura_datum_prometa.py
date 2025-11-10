"""add_index_on_faktura_datum_prometa

Revision ID: a135f4f16914
Revises: 08edd9391e6e
Create Date: 2025-11-10 20:54:45.022201

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a135f4f16914'
down_revision = '08edd9391e6e'
branch_labels = None
depends_on = None


def upgrade():
    # Add index on faktura.datum_prometa for improved performance on rolling limit queries
    op.create_index(
        'idx_faktura_datum_prometa',
        'faktura',
        ['datum_prometa'],
        unique=False
    )


def downgrade():
    # Remove index on faktura.datum_prometa
    op.drop_index('idx_faktura_datum_prometa', table_name='faktura')
