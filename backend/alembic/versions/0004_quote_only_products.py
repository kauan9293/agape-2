"""Mark products that require a WhatsApp quote instead of fixed-price checkout."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0004_quote_only_products"
down_revision = "0003_item_stock_reservations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("products")}
    if "is_quote_only" not in columns:
        op.add_column("products", sa.Column("is_quote_only", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("products")}
    if "is_quote_only" in columns:
        op.drop_column("products", "is_quote_only")