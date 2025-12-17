"""add_custodian_and_town_to_schools

Revision ID: bcb096f1ca91
Revises: 04b2520d2763
Create Date: 2025-12-12 14:22:04.183215

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bcb096f1ca91'
down_revision = '04b2520d2763'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('schools', sa.Column('custodian', sa.String(), nullable=True))
    op.add_column('schools', sa.Column('town', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('schools', 'town')
    op.drop_column('schools', 'custodian')