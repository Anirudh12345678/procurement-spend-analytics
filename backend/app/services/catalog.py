from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models import BusinessUnit, Category, Item, PurchaseOrder, Supplier
from app.schemas.api import PaginatedResponse, PaginationParams
from app.schemas.catalog import (
    BusinessUnitResponse,
    CategoryResponse,
    ItemResponse,
    SupplierDetail,
    SupplierListItem,
)

FOUR_PLACES = Decimal("0.0001")


def _decimal(value: object | None) -> Decimal:
    return Decimal(str(value or 0)).quantize(FOUR_PLACES, rounding=ROUND_HALF_UP)


def _percent(part: object | None, total: object | None) -> Decimal:
    denominator = Decimal(str(total or 0))
    if denominator == 0:
        return _decimal(0)
    return _decimal(Decimal(str(part or 0)) / denominator * 100)


class CatalogService:
    def __init__(self, session: Session):
        self.session = session

    def suppliers(
        self,
        pagination: PaginationParams,
        *,
        search: str | None = None,
        country: str | None = None,
    ) -> PaginatedResponse[SupplierListItem]:
        conditions = []
        if search:
            pattern = f"%{search}%"
            conditions.append(
                or_(Supplier.supplier_name.ilike(pattern), Supplier.supplier_id.ilike(pattern))
            )
        if country:
            conditions.append(Supplier.supplier_country == country)
        total = (
            self.session.scalar(select(func.count()).select_from(Supplier).where(*conditions)) or 0
        )
        rows = self.session.execute(
            select(Supplier.supplier_id, Supplier.supplier_name, Supplier.supplier_country)
            .where(*conditions)
            .order_by(Supplier.supplier_name)
            .offset(pagination.offset)
            .limit(pagination.page_size)
        ).all()
        return PaginatedResponse.create(
            items=[
                SupplierListItem(
                    supplier_id=row.supplier_id,
                    supplier_name=row.supplier_name,
                    country=row.supplier_country,
                )
                for row in rows
            ],
            total=int(total),
            pagination=pagination,
        )

    def supplier(self, supplier_id: str) -> SupplierDetail | None:
        late = PurchaseOrder.actual_delivery_date > PurchaseOrder.promised_delivery_date
        row = self.session.execute(
            select(
                Supplier.supplier_id,
                Supplier.supplier_name,
                Supplier.supplier_country,
                func.coalesce(func.sum(PurchaseOrder.line_total), 0).label("spend"),
                func.count(PurchaseOrder.po_id).label("orders"),
                func.coalesce(func.sum(PurchaseOrder.quantity), 0).label("quantity"),
                func.sum(case((PurchaseOrder.on_contract.is_(True), 1), else_=0)).label(
                    "on_contract_orders"
                ),
                func.sum(case((PurchaseOrder.quality_rejected.is_(True), 1), else_=0)).label(
                    "rejected_orders"
                ),
                func.sum(case((late, 1), else_=0)).label("late_orders"),
            )
            .outerjoin(PurchaseOrder, Supplier.supplier_id == PurchaseOrder.supplier_id)
            .where(Supplier.supplier_id == supplier_id)
            .group_by(
                Supplier.supplier_id,
                Supplier.supplier_name,
                Supplier.supplier_country,
            )
        ).one_or_none()
        if row is None:
            return None
        return SupplierDetail(
            supplier_id=row.supplier_id,
            supplier_name=row.supplier_name,
            country=row.supplier_country,
            total_spend=_decimal(row.spend),
            transaction_count=int(row.orders),
            total_quantity=_decimal(row.quantity),
            on_contract_percent=_percent(row.on_contract_orders, row.orders),
            rejection_rate_percent=_percent(row.rejected_orders, row.orders),
            late_delivery_rate_percent=_percent(row.late_orders, row.orders),
        )

    def categories(self) -> list[CategoryResponse]:
        rows = self.session.execute(
            select(
                Category.category_id,
                Category.category_name,
                func.count(func.distinct(Item.item_id)).label("item_count"),
                func.coalesce(func.sum(PurchaseOrder.line_total), 0).label("spend"),
            )
            .outerjoin(Item, Category.category_id == Item.category_id)
            .outerjoin(PurchaseOrder, Item.item_id == PurchaseOrder.item_id)
            .group_by(Category.category_id, Category.category_name)
            .order_by(Category.category_name)
        ).all()
        return [
            CategoryResponse(
                category_id=int(row.category_id),
                category_name=row.category_name,
                item_count=int(row.item_count),
                total_spend=_decimal(row.spend),
            )
            for row in rows
        ]

    def items(
        self,
        pagination: PaginationParams,
        *,
        category_id: int | None = None,
        search: str | None = None,
    ) -> PaginatedResponse[ItemResponse]:
        conditions = []
        if category_id is not None:
            conditions.append(Item.category_id == category_id)
        if search:
            conditions.append(Item.item_name.ilike(f"%{search}%"))
        total = self.session.scalar(select(func.count()).select_from(Item).where(*conditions)) or 0
        rows = self.session.execute(
            select(
                Item.item_id,
                Item.item_name,
                Category.category_id,
                Category.category_name,
                func.count(func.distinct(PurchaseOrder.supplier_id)).label("supplier_count"),
                func.coalesce(func.sum(PurchaseOrder.line_total), 0).label("spend"),
            )
            .join(Category, Item.category_id == Category.category_id)
            .outerjoin(PurchaseOrder, Item.item_id == PurchaseOrder.item_id)
            .where(*conditions)
            .group_by(
                Item.item_id,
                Item.item_name,
                Category.category_id,
                Category.category_name,
            )
            .order_by(Item.item_name)
            .offset(pagination.offset)
            .limit(pagination.page_size)
        ).all()
        return PaginatedResponse.create(
            items=[
                ItemResponse(
                    item_id=int(row.item_id),
                    item_name=row.item_name,
                    category_id=int(row.category_id),
                    category_name=row.category_name,
                    supplier_count=int(row.supplier_count),
                    total_spend=_decimal(row.spend),
                )
                for row in rows
            ],
            total=int(total),
            pagination=pagination,
        )

    def business_units(self) -> list[BusinessUnitResponse]:
        rows = self.session.execute(
            select(
                BusinessUnit.business_unit_id,
                BusinessUnit.business_unit_name,
                func.count(PurchaseOrder.po_id).label("orders"),
                func.coalesce(func.sum(PurchaseOrder.line_total), 0).label("spend"),
            )
            .outerjoin(
                PurchaseOrder,
                BusinessUnit.business_unit_id == PurchaseOrder.business_unit_id,
            )
            .group_by(BusinessUnit.business_unit_id, BusinessUnit.business_unit_name)
            .order_by(BusinessUnit.business_unit_name)
        ).all()
        return [
            BusinessUnitResponse(
                business_unit_id=int(row.business_unit_id),
                business_unit_name=row.business_unit_name,
                transaction_count=int(row.orders),
                total_spend=_decimal(row.spend),
            )
            for row in rows
        ]
