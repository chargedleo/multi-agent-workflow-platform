"""Add workflow_approvals table and approval_status to workflow_runs.

Revision ID: 005_human_approval
Revises: 004_workflow_validation
Create Date: 2026-10-08 19:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = '005_human_approval'
down_revision: Union[str, None] = '004_workflow_validation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add approval_status column to workflow_runs
    op.add_column(
        'workflow_runs',
        sa.Column('approval_status', sa.String(length=32), nullable=True)
    )
    op.create_index(
        'ix_workflow_runs_approval_status',
        'workflow_runs',
        ['approval_status'],
        unique=False
    )

    # 2. Create workflow_approvals table
    op.create_table(
        'workflow_approvals',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'workflow_run_id',
            UUID(as_uuid=True),
            sa.ForeignKey('workflow_runs.id', ondelete='CASCADE'),
            nullable=False
        ),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='PENDING'),
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('decided_by', sa.String(length=128), nullable=True),
        sa.Column('decision', sa.String(length=32), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('revision_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('metadata', JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index(
        'ix_workflow_approvals_workflow_run_id',
        'workflow_approvals',
        ['workflow_run_id'],
        unique=False
    )
    op.create_index(
        'ix_workflow_approvals_status',
        'workflow_approvals',
        ['status'],
        unique=False
    )
    op.create_index(
        'ix_workflow_approvals_status_requested_at',
        'workflow_approvals',
        ['status', 'requested_at'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_workflow_approvals_status_requested_at', table_name='workflow_approvals')
    op.drop_index('ix_workflow_approvals_status', table_name='workflow_approvals')
    op.drop_index('ix_workflow_approvals_workflow_run_id', table_name='workflow_approvals')
    op.drop_table('workflow_approvals')
    op.drop_index('ix_workflow_runs_approval_status', table_name='workflow_runs')
    op.drop_column('workflow_runs', 'approval_status')
