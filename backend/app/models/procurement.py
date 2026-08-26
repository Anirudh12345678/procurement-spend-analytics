from datetime import date, datetime
from decimal import Decimal
from typing import ClassVar

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

MONEY = Numeric(18, 4)
RATE = Numeric(8, 4)
BIGINT_PK = BigInteger().with_variant(Integer, "sqlite")


class Supplier(Base):
    __tablename__ = "suppliers"
    __table_args__ = (
        UniqueConstraint("supplier_name", name="uq_suppliers_supplier_name"),
        Index("ix_suppliers_country", "supplier_country"),
    )

    supplier_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    supplier_country: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(back_populates="supplier")
    cost_opportunities: Mapped[list["CostOpportunity"]] = relationship(back_populates="supplier")


class Category(Base):
    __tablename__ = "categories"

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)

    items: Mapped[list["Item"]] = relationship(back_populates="category")


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        UniqueConstraint("item_name", "category_id", name="uq_items_name_category"),
        Index("ix_items_category_id", "category_id"),
    )

    item_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.category_id", ondelete="RESTRICT"), nullable=False
    )

    category: Mapped[Category] = relationship(back_populates="items")
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(back_populates="item")
    benchmark: Mapped["ItemBenchmark | None"] = relationship(back_populates="item", uselist=False)
    cost_opportunities: Mapped[list["CostOpportunity"]] = relationship(back_populates="item")


class BusinessUnit(Base):
    __tablename__ = "business_units"

    business_unit_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    business_unit_name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)

    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(back_populates="business_unit")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price >= 0", name="unit_price_nonnegative"),
        CheckConstraint("line_total >= 0", name="line_total_nonnegative"),
        CheckConstraint(
            "promised_delivery_date >= order_date", name="promised_delivery_not_before_order"
        ),
        CheckConstraint(
            "actual_delivery_date >= order_date", name="actual_delivery_not_before_order"
        ),
        Index("ix_purchase_orders_order_date", "order_date"),
        Index("ix_purchase_orders_supplier_order_date", "supplier_id", "order_date"),
        Index("ix_purchase_orders_item_order_date", "item_id", "order_date"),
        Index("ix_purchase_orders_business_unit_order_date", "business_unit_id", "order_date"),
    )

    po_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    promised_delivery_date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_delivery_date: Mapped[date] = mapped_column(Date, nullable=False)
    supplier_id: Mapped[str] = mapped_column(
        ForeignKey("suppliers.supplier_id", ondelete="RESTRICT"), nullable=False
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.item_id", ondelete="RESTRICT"), nullable=False
    )
    business_unit_id: Mapped[int] = mapped_column(
        ForeignKey("business_units.business_unit_id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    line_total: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    payment_terms: Mapped[str] = mapped_column(String(100), nullable=False)
    on_contract: Mapped[bool] = mapped_column(Boolean, nullable=False)
    quality_rejected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    supplier: Mapped[Supplier] = relationship(back_populates="purchase_orders")
    item: Mapped[Item] = relationship(back_populates="purchase_orders")
    business_unit: Mapped[BusinessUnit] = relationship(back_populates="purchase_orders")


class ItemBenchmark(Base):
    __tablename__ = "item_benchmarks"
    __table_args__ = (
        CheckConstraint("supplier_count >= 0", name="supplier_count_nonnegative"),
        CheckConstraint("total_quantity >= 0", name="total_quantity_nonnegative"),
        CheckConstraint("total_spend >= 0", name="total_spend_nonnegative"),
    )

    benchmark_id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.item_id", ondelete="CASCADE"), nullable=False, unique=True
    )
    benchmark_price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    min_price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    max_price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    median_price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    p25_price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    p75_price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    supplier_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_quantity: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    total_spend: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    item: Mapped[Item] = relationship(back_populates="benchmark")


class CostOpportunity(Base):
    __tablename__ = "cost_opportunities"

    OPPORTUNITY_TYPES: ClassVar[tuple[str, ...]] = (
        "PRICE_OPTIMIZATION",
        "CONTRACT_LEAKAGE",
        "SUPPLIER_CONSOLIDATION",
        "SUPPLIER_PERFORMANCE",
    )
    PRIORITY_LEVELS: ClassVar[tuple[str, ...]] = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
    STATUSES: ClassVar[tuple[str, ...]] = (
        "OPEN",
        "IN_REVIEW",
        "ACCEPTED",
        "REJECTED",
        "COMPLETED",
        "STALE",
    )

    __table_args__ = (
        CheckConstraint(
            "opportunity_type IN ('PRICE_OPTIMIZATION', 'CONTRACT_LEAKAGE', "
            "'SUPPLIER_CONSOLIDATION', 'SUPPLIER_PERFORMANCE')",
            name="valid_opportunity_type",
        ),
        CheckConstraint(
            "priority_level IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')",
            name="valid_priority_level",
        ),
        CheckConstraint(
            "status IN ('OPEN', 'IN_REVIEW', 'ACCEPTED', 'REJECTED', 'COMPLETED', 'STALE')",
            name="valid_status",
        ),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1", name="confidence_score_range"
        ),
        CheckConstraint(
            "priority_score >= 0 AND priority_score <= 100", name="priority_score_range"
        ),
        CheckConstraint("estimated_savings >= 0", name="estimated_savings_nonnegative"),
        CheckConstraint("review_spend >= 0", name="review_spend_nonnegative"),
        UniqueConstraint(
            "opportunity_type",
            "item_id",
            "supplier_id",
            name="uq_cost_opportunities_type_item_supplier",
            postgresql_nulls_not_distinct=True,
        ),
        Index("ix_cost_opportunities_priority_status", "priority_level", "status"),
        Index("ix_cost_opportunities_item_id", "item_id"),
        Index("ix_cost_opportunities_supplier_id", "supplier_id"),
    )

    opportunity_id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    opportunity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.item_id", ondelete="CASCADE"), nullable=False
    )
    supplier_id: Mapped[str | None] = mapped_column(
        ForeignKey("suppliers.supplier_id", ondelete="SET NULL"), nullable=True
    )
    actual_price: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    benchmark_price: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    price_variance_percent: Mapped[Decimal | None] = mapped_column(RATE, nullable=True)
    quantity: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    estimated_savings: Mapped[Decimal] = mapped_column(MONEY, nullable=False, default=0)
    review_spend: Mapped[Decimal] = mapped_column(MONEY, nullable=False, default=0)
    confidence_score: Mapped[Decimal] = mapped_column(RATE, nullable=False)
    priority_score: Mapped[Decimal] = mapped_column(RATE, nullable=False)
    priority_level: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    supporting_metrics: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    item: Mapped[Item] = relationship(back_populates="cost_opportunities")
    supplier: Mapped[Supplier | None] = relationship(back_populates="cost_opportunities")
    recommendations: Mapped[list["AIRecommendation"]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan"
    )


class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"
    __table_args__ = (
        UniqueConstraint(
            "opportunity_id",
            "model_name",
            "prompt_version",
            name="uq_ai_recommendations_opportunity_model_prompt",
        ),
        Index("ix_ai_recommendations_opportunity_id", "opportunity_id"),
    )

    recommendation_id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    opportunity_id: Mapped[int] = mapped_column(
        ForeignKey("cost_opportunities.opportunity_id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_impact: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    risks: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_steps: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    context_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    opportunity: Mapped[CostOpportunity] = relationship(back_populates="recommendations")
