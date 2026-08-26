from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import BusinessUnit, Category, Item, PurchaseOrder, Supplier
from app.schemas.imports import DatabaseVerification


def verify_database(session: Session) -> DatabaseVerification:
    """Return referential-integrity and aggregate checks for the imported dataset."""

    duplicate_subquery = (
        select(PurchaseOrder.po_id)
        .group_by(PurchaseOrder.po_id)
        .having(func.count(PurchaseOrder.po_id) > 1)
        .subquery()
    )
    total_spend = session.scalar(select(func.coalesce(func.sum(PurchaseOrder.line_total), 0)))

    return DatabaseVerification(
        supplier_count=session.scalar(select(func.count()).select_from(Supplier)) or 0,
        category_count=session.scalar(select(func.count()).select_from(Category)) or 0,
        item_count=session.scalar(select(func.count()).select_from(Item)) or 0,
        business_unit_count=session.scalar(select(func.count()).select_from(BusinessUnit)) or 0,
        purchase_order_count=session.scalar(select(func.count()).select_from(PurchaseOrder)) or 0,
        total_spend=Decimal(total_spend),
        duplicate_po_ids=session.scalar(select(func.count()).select_from(duplicate_subquery)) or 0,
        orphan_supplier_relationships=session.scalar(
            select(func.count())
            .select_from(PurchaseOrder)
            .outerjoin(Supplier)
            .where(Supplier.supplier_id.is_(None))
        )
        or 0,
        orphan_item_relationships=session.scalar(
            select(func.count())
            .select_from(PurchaseOrder)
            .outerjoin(Item)
            .where(Item.item_id.is_(None))
        )
        or 0,
        orphan_business_unit_relationships=session.scalar(
            select(func.count())
            .select_from(PurchaseOrder)
            .outerjoin(BusinessUnit)
            .where(BusinessUnit.business_unit_id.is_(None))
        )
        or 0,
    )
