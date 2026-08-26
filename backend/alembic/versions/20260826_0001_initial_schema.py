"""Create normalized procurement schema.

Revision ID: 20260826_0001
Revises:
Create Date: 2026-08-26
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260826_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "business_units",
        sa.Column("business_unit_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("business_unit_name", sa.String(length=150), nullable=False),
        sa.PrimaryKeyConstraint("business_unit_id", name=op.f("pk_business_units")),
        sa.UniqueConstraint(
            "business_unit_name", name=op.f("uq_business_units_business_unit_name")
        ),
    )
    op.create_table(
        "categories",
        sa.Column("category_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("category_name", sa.String(length=150), nullable=False),
        sa.PrimaryKeyConstraint("category_id", name=op.f("pk_categories")),
        sa.UniqueConstraint("category_name", name=op.f("uq_categories_category_name")),
    )
    op.create_table(
        "suppliers",
        sa.Column("supplier_id", sa.String(length=64), nullable=False),
        sa.Column("supplier_name", sa.String(length=255), nullable=False),
        sa.Column("supplier_country", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("supplier_id", name=op.f("pk_suppliers")),
        sa.UniqueConstraint("supplier_name", name="uq_suppliers_supplier_name"),
    )
    op.create_index("ix_suppliers_country", "suppliers", ["supplier_country"], unique=False)
    op.create_table(
        "items",
        sa.Column("item_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("item_name", sa.String(length=255), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.category_id"],
            name=op.f("fk_items_category_id_categories"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("item_id", name=op.f("pk_items")),
        sa.UniqueConstraint("item_name", "category_id", name="uq_items_name_category"),
    )
    op.create_index("ix_items_category_id", "items", ["category_id"], unique=False)
    op.create_table(
        "item_benchmarks",
        sa.Column("benchmark_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("benchmark_price", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("min_price", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("max_price", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("median_price", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("p25_price", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("p75_price", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("supplier_count", sa.Integer(), nullable=False),
        sa.Column("total_quantity", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("total_spend", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "supplier_count >= 0", name=op.f("ck_item_benchmarks_supplier_count_nonnegative")
        ),
        sa.CheckConstraint(
            "total_quantity >= 0", name=op.f("ck_item_benchmarks_total_quantity_nonnegative")
        ),
        sa.CheckConstraint(
            "total_spend >= 0", name=op.f("ck_item_benchmarks_total_spend_nonnegative")
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.item_id"],
            name=op.f("fk_item_benchmarks_item_id_items"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("benchmark_id", name=op.f("pk_item_benchmarks")),
        sa.UniqueConstraint("item_id", name=op.f("uq_item_benchmarks_item_id")),
    )
    op.create_table(
        "purchase_orders",
        sa.Column("po_id", sa.String(length=64), nullable=False),
        sa.Column("order_date", sa.Date(), nullable=False),
        sa.Column("promised_delivery_date", sa.Date(), nullable=False),
        sa.Column("actual_delivery_date", sa.Date(), nullable=False),
        sa.Column("supplier_id", sa.String(length=64), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("business_unit_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("line_total", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("payment_terms", sa.String(length=100), nullable=False),
        sa.Column("on_contract", sa.Boolean(), nullable=False),
        sa.Column("quality_rejected", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "actual_delivery_date >= order_date",
            name=op.f("ck_purchase_orders_actual_delivery_not_before_order"),
        ),
        sa.CheckConstraint(
            "line_total >= 0", name=op.f("ck_purchase_orders_line_total_nonnegative")
        ),
        sa.CheckConstraint(
            "promised_delivery_date >= order_date",
            name=op.f("ck_purchase_orders_promised_delivery_not_before_order"),
        ),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_purchase_orders_quantity_positive")),
        sa.CheckConstraint(
            "unit_price >= 0", name=op.f("ck_purchase_orders_unit_price_nonnegative")
        ),
        sa.ForeignKeyConstraint(
            ["business_unit_id"],
            ["business_units.business_unit_id"],
            name=op.f("fk_purchase_orders_business_unit_id_business_units"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.item_id"],
            name=op.f("fk_purchase_orders_item_id_items"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.supplier_id"],
            name=op.f("fk_purchase_orders_supplier_id_suppliers"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("po_id", name=op.f("pk_purchase_orders")),
    )
    op.create_index(
        "ix_purchase_orders_business_unit_order_date",
        "purchase_orders",
        ["business_unit_id", "order_date"],
        unique=False,
    )
    op.create_index(
        "ix_purchase_orders_item_order_date",
        "purchase_orders",
        ["item_id", "order_date"],
        unique=False,
    )
    op.create_index(
        "ix_purchase_orders_order_date", "purchase_orders", ["order_date"], unique=False
    )
    op.create_index(
        "ix_purchase_orders_supplier_order_date",
        "purchase_orders",
        ["supplier_id", "order_date"],
        unique=False,
    )
    op.create_table(
        "cost_opportunities",
        sa.Column("opportunity_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("opportunity_type", sa.String(length=40), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.String(length=64), nullable=True),
        sa.Column("actual_price", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("benchmark_price", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("price_variance_percent", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("estimated_savings", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("confidence_score", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("priority_score", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("priority_level", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name=op.f("ck_cost_opportunities_confidence_score_range"),
        ),
        sa.CheckConstraint(
            "estimated_savings >= 0",
            name=op.f("ck_cost_opportunities_estimated_savings_nonnegative"),
        ),
        sa.CheckConstraint(
            "opportunity_type IN ('PRICE_OPTIMIZATION', 'CONTRACT_LEAKAGE', "
            "'SUPPLIER_CONSOLIDATION', 'SUPPLIER_PERFORMANCE')",
            name=op.f("ck_cost_opportunities_valid_opportunity_type"),
        ),
        sa.CheckConstraint(
            "priority_level IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')",
            name=op.f("ck_cost_opportunities_valid_priority_level"),
        ),
        sa.CheckConstraint(
            "priority_score >= 0 AND priority_score <= 100",
            name=op.f("ck_cost_opportunities_priority_score_range"),
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'IN_REVIEW', 'ACCEPTED', 'REJECTED', 'COMPLETED')",
            name=op.f("ck_cost_opportunities_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.item_id"],
            name=op.f("fk_cost_opportunities_item_id_items"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.supplier_id"],
            name=op.f("fk_cost_opportunities_supplier_id_suppliers"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("opportunity_id", name=op.f("pk_cost_opportunities")),
        sa.UniqueConstraint(
            "opportunity_type",
            "item_id",
            "supplier_id",
            name="uq_cost_opportunities_type_item_supplier",
        ),
    )
    op.create_index(
        "ix_cost_opportunities_item_id", "cost_opportunities", ["item_id"], unique=False
    )
    op.create_index(
        "ix_cost_opportunities_priority_status",
        "cost_opportunities",
        ["priority_level", "status"],
        unique=False,
    )
    op.create_index(
        "ix_cost_opportunities_supplier_id",
        "cost_opportunities",
        ["supplier_id"],
        unique=False,
    )
    op.create_table(
        "ai_recommendations",
        sa.Column("recommendation_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("opportunity_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.Column("estimated_impact", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["cost_opportunities.opportunity_id"],
            name=op.f("fk_ai_recommendations_opportunity_id_cost_opportunities"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("recommendation_id", name=op.f("pk_ai_recommendations")),
        sa.UniqueConstraint(
            "opportunity_id",
            "model_name",
            "prompt_version",
            name="uq_ai_recommendations_opportunity_model_prompt",
        ),
    )
    op.create_index(
        "ix_ai_recommendations_opportunity_id",
        "ai_recommendations",
        ["opportunity_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ai_recommendations_opportunity_id", table_name="ai_recommendations")
    op.drop_table("ai_recommendations")
    op.drop_index("ix_cost_opportunities_supplier_id", table_name="cost_opportunities")
    op.drop_index("ix_cost_opportunities_priority_status", table_name="cost_opportunities")
    op.drop_index("ix_cost_opportunities_item_id", table_name="cost_opportunities")
    op.drop_table("cost_opportunities")
    op.drop_index("ix_purchase_orders_supplier_order_date", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_order_date", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_item_order_date", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_business_unit_order_date", table_name="purchase_orders")
    op.drop_table("purchase_orders")
    op.drop_table("item_benchmarks")
    op.drop_index("ix_items_category_id", table_name="items")
    op.drop_table("items")
    op.drop_index("ix_suppliers_country", table_name="suppliers")
    op.drop_table("suppliers")
    op.drop_table("categories")
    op.drop_table("business_units")
