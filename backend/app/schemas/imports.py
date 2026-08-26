from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

LINE_TOTAL_TOLERANCE = Decimal("0.01")


class CsvPurchaseOrderRow(BaseModel):
    """Validated representation of one source CSV record."""

    po_id: str = Field(min_length=1, max_length=64)
    order_date: date
    promised_delivery_date: date
    actual_delivery_date: date
    supplier_id: str = Field(min_length=1, max_length=64)
    supplier_name: str = Field(min_length=1, max_length=255)
    supplier_country: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=150)
    item: str = Field(min_length=1, max_length=255)
    business_unit: str = Field(min_length=1, max_length=150)
    unit_price: Decimal = Field(ge=0, max_digits=18, decimal_places=4)
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=4)
    line_total: Decimal = Field(ge=0, max_digits=18, decimal_places=4)
    payment_terms: str = Field(min_length=1, max_length=100)
    on_contract: bool
    quality_rejected: bool

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("on_contract", "quality_rejected", mode="before")
    @classmethod
    def validate_boolean(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        normalized = str(value).strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
        raise ValueError("must be either True or False")

    @model_validator(mode="after")
    def validate_dates_and_total(self) -> "CsvPurchaseOrderRow":
        if self.promised_delivery_date < self.order_date:
            raise ValueError("promised_delivery_date cannot be before order_date")
        if self.actual_delivery_date < self.order_date:
            raise ValueError("actual_delivery_date cannot be before order_date")

        calculated = self.quantity * self.unit_price
        if abs(self.line_total - calculated) > LINE_TOTAL_TOLERANCE:
            raise ValueError(
                "line_total does not match quantity * unit_price within 0.01 "
                f"(expected {calculated}, found {self.line_total})"
            )
        return self


class RejectedRow(BaseModel):
    row_number: int
    po_id: str | None = None
    errors: list[str]
    raw_data: dict[str, str | None]


class ValidationReport(BaseModel):
    source_rows: int
    valid_rows: list[CsvPurchaseOrderRow]
    rejected_rows: list[RejectedRow]
    extra_columns: list[str] = Field(default_factory=list)

    @property
    def valid_count(self) -> int:
        return len(self.valid_rows)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected_rows)


class ImportSummary(BaseModel):
    source_file: str
    source_rows: int
    valid_rows: int
    rejected_rows: int
    inserted_purchase_orders: int
    updated_purchase_orders: int
    supplier_count: int
    category_count: int
    item_count: int
    business_unit_count: int
    purchase_order_count: int
    total_spend: Decimal
    rejection_report: str | None = None


class DatabaseVerification(BaseModel):
    supplier_count: int
    category_count: int
    item_count: int
    business_unit_count: int
    purchase_order_count: int
    total_spend: Decimal
    duplicate_po_ids: int
    orphan_supplier_relationships: int
    orphan_item_relationships: int
    orphan_business_unit_relationships: int

    @property
    def is_valid(self) -> bool:
        return (
            self.duplicate_po_ids == 0
            and self.orphan_supplier_relationships == 0
            and self.orphan_item_relationships == 0
            and self.orphan_business_unit_relationships == 0
        )
