"""Initial workflow persistence tables.

Revision ID: 001_initial
Revises: 
Create Date: 2026-10-07 17:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create workflow_runs table
    op.create_table(
        'workflow_runs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('request_id', sa.UUID(), nullable=False),
        sa.Column('user_query', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='PENDING', nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.BigInteger(), nullable=True),
        sa.Column('final_answer', sa.Text(), nullable=True),
        sa.Column('key_points', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('plan', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('research_results', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('errors', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_workflow_runs_request_id'), 'workflow_runs', ['request_id'], unique=False)
    op.create_index(op.f('ix_workflow_runs_status'), 'workflow_runs', ['status'], unique=False)
    op.create_index(op.f('ix_workflow_runs_started_at'), 'workflow_runs', ['started_at'], unique=False)
    op.create_index(op.f('ix_workflow_runs_created_at'), 'workflow_runs', ['created_at'], unique=False)
    op.create_index('ix_workflow_runs_status_created_at', 'workflow_runs', ['status', 'created_at'], unique=False)

    # 2. Create workflow_steps table
    op.create_table(
        'workflow_steps',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('run_id', sa.UUID(), nullable=False),
        sa.Column('agent_name', sa.String(length=64), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='PENDING', nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.BigInteger(), nullable=True),
        sa.Column('input_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['workflow_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_workflow_steps_run_id'), 'workflow_steps', ['run_id'], unique=False)
    op.create_index(op.f('ix_workflow_steps_agent_name'), 'workflow_steps', ['agent_name'], unique=False)
    op.create_index(op.f('ix_workflow_steps_status'), 'workflow_steps', ['status'], unique=False)
    op.create_index('ix_workflow_steps_run_step_order', 'workflow_steps', ['run_id', 'step_order'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_workflow_steps_run_step_order', table_name='workflow_steps')
    op.drop_index(op.f('ix_workflow_steps_status'), table_name='workflow_steps')
    op.drop_index(op.f('ix_workflow_steps_agent_name'), table_name='workflow_steps')
    op.drop_index(op.f('ix_workflow_steps_run_id'), table_name='workflow_steps')
    op.drop_table('workflow_steps')

    op.drop_index('ix_workflow_runs_status_created_at', table_name='workflow_runs')
    op.drop_index(op.f('ix_workflow_runs_created_at'), table_name='workflow_runs')
    op.drop_index(op.f('ix_workflow_runs_started_at'), table_name='workflow_runs')
    op.drop_index(op.f('ix_workflow_runs_status'), table_name='workflow_runs')
    op.drop_index(op.f('ix_workflow_runs_request_id'), table_name='workflow_runs')
    op.drop_table('workflow_runs')
