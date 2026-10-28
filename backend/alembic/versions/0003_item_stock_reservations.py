"""Track stock quantities reserved for each order line."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0003_item_stock_reservations"
down_revision = "0002_demo_and_stock_reservation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("order_items")}
    if "reserved_product_stock" not in columns:
        op.add_column("order_items", sa.Column("reserved_product_stock", sa.Integer(), nullable=False, server_default="0"))
    if "reserved_variant_stock" not in columns:
        op.add_column("order_items", sa.Column("reserved_variant_stock", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("order_items")}
    if "reserved_variant_stock" in columns:
        op.drop_column("order_items", "reserved_variant_stock")
    if "reserved_product_stock" in columns:
        op.drop_column("order_items", "reserved_product_stock")