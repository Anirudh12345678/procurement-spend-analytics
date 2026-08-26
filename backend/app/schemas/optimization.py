from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class BenchmarkResponse(BaseModel):
    benchmark_id: int
    item_id: int
    item_name: str
    category_id: int
    category_name: str
    benchmark_price: Decimal
    min_price: Decimal
    max_price: Decimal
    median_price: Decimal
    p25_price: Decimal
    p75_price: Decimal
    supplier_count: int
    total_quantity: Decimal
    total_spend: Decimal
    calculated_at: datetime


class OpportunityResponse(BaseModel):
    opportunity_id: int
    opportunity_type: str
    item_id: int
    item_name: str
    category_id: int
    category_name: str
    supplier_id: str | None
    supplier_name: str | None
    actual_price: Decimal | None
    benchmark_price: Decimal | None
    price_variance_percent: Decimal | None
    quantity: Decimal | None
    estimated_savings: Decimal
    review_spend: Decimal
    confidence_score: Decimal
    priority_score: Decimal
    priority_level: str
    status: str
    supporting_metrics: dict[str, object]
    created_at: datetime


class OpportunitySummary(BaseModel):
    active_opportunity_count: int
    estimated_price_optimization_savings: Decimal
    review_spend: Decimal
    critical_count: int
    high_priority_count: int
    price_optimization_count: int
    contract_leakage_count: int
    supplier_consolidation_count: int
    supplier_performance_count: int
    savings_note: str
