from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AnalyticsFilters(BaseModel):
    """Common inclusive filters accepted by deterministic analytics queries."""

    date_from: date | None = None
    date_to: date | None = None
    supplier_id: str | None = Field(default=None, min_length=1, max_length=64)
    category_id: int | None = Field(default=None, ge=1)
    business_unit_id: int | None = Field(default=None, ge=1)
    country: str | None = Field(default=None, min_length=1, max_length=100)

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_date_range(self) -> "AnalyticsFilters":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from cannot be after date_to")
        return self


class DashboardSummary(BaseModel):
    total_spend: Decimal
    total_orders: int
    average_order_value: Decimal
    supplier_count: int
    category_count: int
    business_unit_count: int


class SupplierAnalyticsItem(BaseModel):
    supplier_id: str
    supplier_name: str
    country: str
    spend: Decimal
    share_percent: Decimal
    transaction_count: int
    average_order_value: Decimal
    total_quantity: Decimal
    rank: int


class SupplierConcentration(BaseModel):
    total_spend: Decimal
    supplier_count: int
    top_5_spend: Decimal
    top_5_concentration_percent: Decimal
    top_10_spend: Decimal
    top_10_concentration_percent: Decimal


class CategoryAnalyticsItem(BaseModel):
    category_id: int
    category_name: str
    spend: Decimal
    share_percent: Decimal
    transaction_count: int
    average_order_value: Decimal
    supplier_count: int


class BusinessUnitAnalyticsItem(BaseModel):
    business_unit_id: int
    business_unit_name: str
    spend: Decimal
    share_percent: Decimal
    transaction_count: int


class MonthlyAnalyticsItem(BaseModel):
    month: date
    spend: Decimal
    transaction_count: int
    average_order_value: Decimal
    growth_percent: Decimal | None


class ContractAnalytics(BaseModel):
    total_spend: Decimal
    total_orders: int
    on_contract_spend: Decimal
    off_contract_spend: Decimal
    on_contract_percent: Decimal
    off_contract_percent: Decimal
    on_contract_order_count: int
    off_contract_order_count: int


class SupplierQualityMetric(BaseModel):
    supplier_id: str
    supplier_name: str
    country: str
    total_orders: int
    rejected_order_count: int
    rejection_rate_percent: Decimal
    rejected_spend: Decimal


class QualityAnalytics(BaseModel):
    total_orders: int
    rejected_order_count: int
    rejection_rate_percent: Decimal
    rejected_spend: Decimal
    suppliers: list[SupplierQualityMetric]


class SupplierDeliveryMetric(BaseModel):
    supplier_id: str
    supplier_name: str
    country: str
    total_orders: int
    late_order_count: int
    late_delivery_rate_percent: Decimal
    average_delay_days: Decimal


class DeliveryAnalytics(BaseModel):
    total_orders: int
    late_order_count: int
    late_delivery_rate_percent: Decimal
    average_delay_days: Decimal
    suppliers: list[SupplierDeliveryMetric]
