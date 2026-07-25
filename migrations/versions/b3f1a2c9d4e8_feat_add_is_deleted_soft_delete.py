"""feat: add is_deleted for soft delete

Revision ID: b3f1a2c9d4e8
Revises: 236d84cd7616
Create Date: 2026-07-25 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b3f1a2c9d4e8"
down_revision: Union[str, Sequence[str], None] = "236d84cd7616"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = [
    "categories",
    "units_of_measure",
    "ingredients",
    "suppliers",
    "supplier_ingredients",
]


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(
            table,
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        )


def downgrade() -> None:
    for table in _TABLES:
        op.drop_column(table, "is_deleted")
