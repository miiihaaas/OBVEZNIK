"""create_kpo_entries_table

Revision ID: 08edd9391e6e
Revises: d409b6335df1
Create Date: 2025-11-09 18:50:35.416450

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '08edd9391e6e'
down_revision = 'd409b6335df1'
branch_labels = None
depends_on = None


def upgrade():
    # Create kpo_entries table
    op.create_table(
        'kpo_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('firma_id', sa.Integer(), nullable=False),
        sa.Column('faktura_id', sa.Integer(), nullable=False),
        sa.Column('redni_broj', sa.Integer(), nullable=False),
        sa.Column('broj_fakture', sa.String(length=50), nullable=False),
        sa.Column('datum_prometa', sa.Date(), nullable=False),
        sa.Column('datum_dospeca', sa.Date(), nullable=False),
        sa.Column('komitent_naziv', sa.String(length=255), nullable=False),
        sa.Column('komitent_pib', sa.String(length=8), nullable=False),
        sa.Column('opis', sa.Text(), nullable=True),
        sa.Column('iznos_rsd', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('valuta', sa.Enum('RSD', 'EUR', 'USD', 'GBP', 'CHF', name='valuta_fakture'), nullable=False),
        sa.Column('status_fakture', sa.Enum('izdata', 'stornirana', name='status_kpo'), nullable=False),
        sa.Column('godina', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['firma_id'], ['pausaln_firma.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['faktura_id'], ['fakture.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    with op.batch_alter_table('kpo_entries', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_kpo_entries_firma_id'), ['firma_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_kpo_entries_faktura_id'), ['faktura_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_kpo_entries_godina'), ['godina'], unique=False)
        batch_op.create_index('idx_firma_godina', ['firma_id', 'godina'], unique=False)
        batch_op.create_unique_constraint('uq_kpo_redni_broj_per_firma_godina', ['firma_id', 'redni_broj', 'godina'])


def downgrade():
    # Drop kpo_entries table
    op.drop_table('kpo_entries')
