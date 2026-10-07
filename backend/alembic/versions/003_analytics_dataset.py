"""Analytics orders dataset table and seed data.

Revision ID: 003_analytics_dataset
Revises: 002_document_ingestion
Create Date: 2026-10-07 19:40:00.000000

"""
import uuid
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003_analytics_dataset'
down_revision: Union[str, None] = '002_document_ingestion'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED_ORDERS = [
    {"order_id": "ORD-1001", "order_date": "2026-01-15", "customer": "Acme Corp", "region": "North", "product": "Cloud Suite", "category": "Software", "quantity": 5, "unit_price": 1200.0, "revenue": 6000.0},
    {"order_id": "ORD-1002", "order_date": "2026-01-18", "customer": "Stark Industries", "region": "West", "product": "Analytics Pro", "category": "Software", "quantity": 10, "unit_price": 850.0, "revenue": 8500.0},
    {"order_id": "ORD-1003", "order_date": "2026-01-20", "customer": "Wayne Enterprises", "region": "South", "product": "Database Plus", "category": "Software", "quantity": 4, "unit_price": 1500.0, "revenue": 6000.0},
    {"order_id": "ORD-1004", "order_date": "2026-01-22", "customer": "Cyberdyne Systems", "region": "East", "product": "Security Shield", "category": "Software", "quantity": 8, "unit_price": 950.0, "revenue": 7600.0},
    {"order_id": "ORD-1005", "order_date": "2026-02-01", "customer": "Umbrella Corp", "region": "West", "product": "Cloud Suite", "category": "Software", "quantity": 12, "unit_price": 1200.0, "revenue": 14400.0},
    {"order_id": "ORD-1006", "order_date": "2026-02-05", "customer": "Oscorp", "region": "North", "product": "Support Enterprise", "category": "Services", "quantity": 2, "unit_price": 2500.0, "revenue": 5000.0},
    {"order_id": "ORD-1007", "order_date": "2026-02-10", "customer": "Initech", "region": "South", "product": "Analytics Pro", "category": "Software", "quantity": 6, "unit_price": 850.0, "revenue": 5100.0},
    {"order_id": "ORD-1008", "order_date": "2026-02-14", "customer": "Hooli", "region": "West", "product": "Database Plus", "category": "Software", "quantity": 15, "unit_price": 1500.0, "revenue": 22500.0},
    {"order_id": "ORD-1009", "order_date": "2026-02-18", "customer": "Massive Dynamic", "region": "East", "product": "Workflow Starter", "category": "Software", "quantity": 20, "unit_price": 300.0, "revenue": 6000.0},
    {"order_id": "ORD-1010", "order_date": "2026-02-25", "customer": "Pied Piper", "region": "West", "product": "Security Shield", "category": "Software", "quantity": 7, "unit_price": 950.0, "revenue": 6650.0},
    {"order_id": "ORD-1011", "order_date": "2026-03-02", "customer": "Globex Corp", "region": "North", "product": "Cloud Suite", "category": "Software", "quantity": 8, "unit_price": 1200.0, "revenue": 9600.0},
    {"order_id": "ORD-1012", "order_date": "2026-03-08", "customer": "Soylent Corp", "region": "South", "product": "Support Enterprise", "category": "Services", "quantity": 3, "unit_price": 2500.0, "revenue": 7500.0},
    {"order_id": "ORD-1013", "order_date": "2026-03-12", "customer": "Dunder Mifflin", "region": "East", "product": "Analytics Pro", "category": "Software", "quantity": 5, "unit_price": 850.0, "revenue": 4250.0},
    {"order_id": "ORD-1014", "order_date": "2026-03-15", "customer": "Wonka Industries", "region": "West", "product": "Cloud Suite", "category": "Software", "quantity": 10, "unit_price": 1200.0, "revenue": 12000.0},
    {"order_id": "ORD-1015", "order_date": "2026-03-20", "customer": "Vandelay Industries", "region": "North", "product": "Database Plus", "category": "Software", "quantity": 6, "unit_price": 1500.0, "revenue": 9000.0},
    {"order_id": "ORD-1016", "order_date": "2026-03-22", "customer": "Aperture Science", "region": "South", "product": "Security Shield", "category": "Software", "quantity": 9, "unit_price": 950.0, "revenue": 8550.0},
    {"order_id": "ORD-1017", "order_date": "2026-03-25", "customer": "Tyrell Corp", "region": "East", "product": "Support Enterprise", "category": "Services", "quantity": 4, "unit_price": 2500.0, "revenue": 10000.0},
    {"order_id": "ORD-1018", "order_date": "2026-03-28", "customer": "Cyberdyne Systems", "region": "West", "product": "Workflow Starter", "category": "Software", "quantity": 25, "unit_price": 300.0, "revenue": 7500.0},
    {"order_id": "ORD-1019", "order_date": "2026-03-30", "customer": "Stark Industries", "region": "North", "product": "Security Shield", "category": "Software", "quantity": 10, "unit_price": 950.0, "revenue": 9500.0},
    {"order_id": "ORD-1020", "order_date": "2026-03-31", "customer": "Acme Corp", "region": "South", "product": "Database Plus", "category": "Software", "quantity": 8, "unit_price": 1500.0, "revenue": 12000.0},
]


def upgrade() -> None:
    # 1. Create analytics_orders table
    analytics_orders_table = op.create_table(
        'analytics_orders',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('order_id', sa.String(length=32), nullable=False),
        sa.Column('order_date', sa.String(length=16), nullable=False),
        sa.Column('customer', sa.String(length=128), nullable=False),
        sa.Column('region', sa.String(length=64), nullable=False),
        sa.Column('product', sa.String(length=128), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Float(), nullable=False),
        sa.Column('revenue', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_analytics_orders_order_id'), 'analytics_orders', ['order_id'], unique=True)
    op.create_index(op.f('ix_analytics_orders_order_date'), 'analytics_orders', ['order_date'], unique=False)
    op.create_index(op.f('ix_analytics_orders_region'), 'analytics_orders', ['region'], unique=False)
    op.create_index(op.f('ix_analytics_orders_product'), 'analytics_orders', ['product'], unique=False)

    # 2. Seed deterministic sample data with generated UUIDs
    rows_to_insert = [
        {
            "id": uuid.uuid4(),
            **order,
        }
        for order in SEED_ORDERS
    ]
    op.bulk_insert(analytics_orders_table, rows_to_insert)


def downgrade() -> None:
    op.drop_index(op.f('ix_analytics_orders_product'), table_name='analytics_orders')
    op.drop_index(op.f('ix_analytics_orders_region'), table_name='analytics_orders')
    op.drop_index(op.f('ix_analytics_orders_order_date'), table_name='analytics_orders')
    op.drop_index(op.f('ix_analytics_orders_order_id'), table_name='analytics_orders')
    op.drop_table('analytics_orders')
