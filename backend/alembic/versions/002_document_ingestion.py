"""Document ingestion and chunking tables.

Revision ID: 002_document_ingestion
Revises: 001_initial
Create Date: 2026-10-07 18:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_document_ingestion'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('checksum', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='PENDING', nullable=False),
        sa.Column('page_count', sa.Integer(), server_default='1', nullable=False),
        sa.Column('chunk_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_documents_checksum'), 'documents', ['checksum'], unique=False)
    op.create_index(op.f('ix_documents_status'), 'documents', ['status'], unique=False)
    op.create_index(op.f('ix_documents_created_at'), 'documents', ['created_at'], unique=False)
    op.create_index('ix_documents_status_created_at', 'documents', ['status', 'created_at'], unique=False)

    # 2. Create document_chunks table
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('page_number', sa.Integer(), server_default='1', nullable=False),
        sa.Column('start_char', sa.Integer(), nullable=True),
        sa.Column('end_char', sa.Integer(), nullable=True),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_document_chunks_document_id'), 'document_chunks', ['document_id'], unique=False)
    op.create_index('ix_document_chunks_document_id_chunk_index', 'document_chunks', ['document_id', 'chunk_index'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_document_chunks_document_id_chunk_index', table_name='document_chunks')
    op.drop_index(op.f('ix_document_chunks_document_id'), table_name='document_chunks')
    op.drop_table('document_chunks')

    op.drop_index('ix_documents_status_created_at', table_name='documents')
    op.drop_index(op.f('ix_documents_created_at'), table_name='documents')
    op.drop_index(op.f('ix_documents_status'), table_name='documents')
    op.drop_index(op.f('ix_documents_checksum'), table_name='documents')
    op.drop_table('documents')
