"""Treat null suppliers as equal for opportunity uniqueness.

Revision ID: 20260826_0002
Revises: 20260826_0001
Create Date: 2026-08-26
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260826_0002"
down_revision: str | None = "20260826_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_cost_opportunities_type_item_supplier",
        "cost_opportunities",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_cost_opportunities_type_item_supplier",
        "cost_opportunities",
        ["opportunity_type", "item_id", "supplier_id"],
        postgresql_nulls_not_distinct=True,
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_cost_opportunities_type_item_supplier",
        "cost_opportunities",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_cost_opportunities_type_item_supplier",
        "cost_opportunities",
        ["opportunity_type", "item_id", "supplier_id"],
    )
