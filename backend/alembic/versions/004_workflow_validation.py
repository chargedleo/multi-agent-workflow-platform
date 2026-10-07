"""Add validation columns to workflow_runs table.

Revision ID: 004_workflow_validation
Revises: 003_analytics_dataset
Create Date: 2026-10-07 20:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004_workflow_validation'
down_revision: Union[str, None] = '003_analytics_dataset'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('workflow_runs', sa.Column('validation_status', sa.String(length=32), nullable=True))
    op.add_column('workflow_runs', sa.Column('validation_score', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('workflow_runs', 'validation_score')
    op.drop_column('workflow_runs', 'validation_status')
