"""add storniranje fields to faktura

Revision ID: 8055af3bbcdc
Revises: b2c3d4e5f6a7
Create Date: 2025-11-09 16:43:55.591144

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8055af3bbcdc'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    # Add optional storniranje audit trail fields to fakture table
    op.add_column('fakture', sa.Column('razlog_storniranja', sa.String(500), nullable=True))
    op.add_column('fakture', sa.Column('stornirana_at', sa.DateTime(), nullable=True))
    op.add_column('fakture', sa.Column('stornirana_by_user_id', sa.Integer(), nullable=True))

    # Add foreign key constraint for stornirana_by_user_id
    op.create_foreign_key(
        'fk_fakture_stornirana_by_user_id',
        'fakture',
        'users',
        ['stornirana_by_user_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    # Drop foreign key constraint
    op.drop_constraint('fk_fakture_stornirana_by_user_id', 'fakture', type_='foreignkey')

    # Drop columns
    op.drop_column('fakture', 'stornirana_by_user_id')
    op.drop_column('fakture', 'stornirana_at')
    op.drop_column('fakture', 'razlog_storniranja')
