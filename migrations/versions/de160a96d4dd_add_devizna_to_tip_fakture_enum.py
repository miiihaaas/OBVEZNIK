"""add devizna to tip_fakture enum

Revision ID: de160a96d4dd
Revises: 8e7d081a7c9a
Create Date: 2025-10-28 17:16:43.869400

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'de160a96d4dd'
down_revision = '8e7d081a7c9a'
branch_labels = None
depends_on = None


def upgrade():
    # Add 'devizna' to tip_fakture ENUM
    op.execute(
        "ALTER TABLE fakture MODIFY COLUMN tip_fakture "
        "ENUM('standardna', 'profaktura', 'avansna', 'devizna') NOT NULL"
    )


def downgrade():
    # Remove 'devizna' from tip_fakture ENUM (reverse migration)
    # WARNING: This will fail if any fakture have tip_fakture='devizna'
    op.execute(
        "ALTER TABLE fakture MODIFY COLUMN tip_fakture "
        "ENUM('standardna', 'profaktura', 'avansna') NOT NULL"
    )
