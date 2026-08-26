from decimal import Decimal

from pydantic import BaseModel


class SupplierListItem(BaseModel):
    supplier_id: str
    supplier_name: str
    country: str


class SupplierDetail(SupplierListItem):
    total_spend: Decimal
    transaction_count: int
    total_quantity: Decimal
    on_contract_percent: Decimal
    rejection_rate_percent: Decimal
    late_delivery_rate_percent: Decimal


class CategoryResponse(BaseModel):
    category_id: int
    category_name: str
    item_count: int
    total_spend: Decimal


class ItemResponse(BaseModel):
    item_id: int
    item_name: str
    category_id: int
    category_name: str
    supplier_count: int
    total_spend: Decimal


class BusinessUnitResponse(BaseModel):
    business_unit_id: int
    business_unit_name: str
    transaction_count: int
    total_spend: Decimal
