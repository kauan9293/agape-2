"""Add demo labels, requested dates, and stock reservation state."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0002_demo_and_stock_reservation"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    product_columns = {column["name"] for column in inspector.get_columns("products")}
    order_columns = {column["name"] for column in inspector.get_columns("orders")}
    if "is_demo" not in product_columns:
        op.add_column("products", sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "requested_for" not in order_columns:
        op.add_column("orders", sa.Column("requested_for", sa.DateTime(timezone=True), nullable=True))
        op.execute(sa.text("UPDATE orders SET requested_for = created_at WHERE requested_for IS NULL"))
    if "stock_reserved" not in order_columns:
        op.add_column("orders", sa.Column("stock_reserved", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    product_columns = {column["name"] for column in inspector.get_columns("products")}
    order_columns = {column["name"] for column in inspector.get_columns("orders")}
    if "stock_reserved" in order_columns:
        op.drop_column("orders", "stock_reserved")
    if "requested_for" in order_columns:
        op.drop_column("orders", "requested_for")
    if "is_demo" in product_columns:
        op.drop_column("products", "is_demo")