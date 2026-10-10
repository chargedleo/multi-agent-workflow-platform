"""Add evaluation_runs and evaluation_case_results tables.

Revision ID: 006_evaluation_engine
Revises: 005_human_approval
Create Date: 2026-10-10 20:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '006_evaluation_engine'
down_revision: Union[str, None] = '005_human_approval'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create evaluation_runs table
    op.create_table(
        'evaluation_runs',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('dataset_name', sa.String(length=128), nullable=False),
        sa.Column('dataset_version', sa.String(length=32), nullable=False),
        sa.Column('dataset_checksum', sa.String(length=64), nullable=True),
        sa.Column('mode', sa.String(length=32), nullable=False, server_default='metric_only'),
        sa.Column('application_version', sa.String(length=32), nullable=False, server_default='0.1.0'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='PENDING'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('configuration_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('aggregate_metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('summary', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_evaluation_runs_dataset_name', 'evaluation_runs', ['dataset_name'], unique=False)
    op.create_index('ix_evaluation_runs_status', 'evaluation_runs', ['status'], unique=False)
    op.create_index('ix_evaluation_runs_created_at', 'evaluation_runs', ['created_at'], unique=False)

    # 2. Create evaluation_case_results table
    op.create_table(
        'evaluation_case_results',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column(
            'evaluation_run_id',
            sa.UUID(),
            sa.ForeignKey('evaluation_runs.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('case_id', sa.String(length=64), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('associated_workflow_run_id', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='COMPLETED'),
        sa.Column('duration_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('metric_results', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('safe_error_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_evaluation_case_results_evaluation_run_id', 'evaluation_case_results', ['evaluation_run_id'], unique=False)
    op.create_index('ix_evaluation_case_results_case_id', 'evaluation_case_results', ['case_id'], unique=False)
    op.create_index('ix_evaluation_case_results_category', 'evaluation_case_results', ['category'], unique=False)
    op.create_index('ix_eval_case_results_run_case', 'evaluation_case_results', ['evaluation_run_id', 'case_id'], unique=False)


def downgrade() -> None:
    op.drop_table('evaluation_case_results')
    op.drop_table('evaluation_runs')
