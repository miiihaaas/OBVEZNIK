"""add zatvorena to status_fakture enum

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-11-07 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Add 'zatvorena' to status ENUM
    op.execute(
        "ALTER TABLE fakture MODIFY COLUMN status "
        "ENUM('draft', 'izdata', 'stornirana', 'konvertovana', 'zatvorena') NOT NULL DEFAULT 'draft'"
    )


def downgrade():
    # Remove 'zatvorena' from status ENUM (reverse migration)
    # WARNING: This will fail if any fakture have status='zatvorena'
    op.execute(
        "ALTER TABLE fakture MODIFY COLUMN status "
        "ENUM('draft', 'izdata', 'stornirana', 'konvertovana') NOT NULL DEFAULT 'draft'"
    )
