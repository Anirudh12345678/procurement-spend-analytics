from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import Integer, Numeric, case, cast, func, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import FunctionElement

from app.models import BusinessUnit, Category, Item, PurchaseOrder, Supplier
from app.schemas.analytics import (
    AnalyticsFilters,
    BusinessUnitAnalyticsItem,
    CategoryAnalyticsItem,
    ContractAnalytics,
    DashboardSummary,
    DeliveryAnalytics,
    MonthlyAnalyticsItem,
    QualityAnalytics,
    SupplierAnalyticsItem,
    SupplierConcentration,
    SupplierDeliveryMetric,
    SupplierQualityMetric,
)

FOUR_PLACES = Decimal("0.0001")
ZERO = Decimal("0.0000")


class DeliveryDelayDays(FunctionElement):
    """Portable SQL expression for calendar days between two dates."""

    type = Numeric(12, 4)
    inherit_cache = True


@compiles(DeliveryDelayDays, "postgresql")
def compile_delivery_delay_postgresql(element, compiler, **kwargs) -> str:
    actual_date, promised_date = list(element.clauses)
    return (
        f"({compiler.process(actual_date, **kwargs)} - {compiler.process(promised_date, **kwargs)})"
    )


@compiles(DeliveryDelayDays, "sqlite")
def compile_delivery_delay_sqlite(element, compiler, **kwargs) -> str:
    actual_date, promised_date = list(element.clauses)
    return (
        f"(julianday({compiler.process(actual_date, **kwargs)}) - "
        f"julianday({compiler.process(promised_date, **kwargs)}))"
    )


def _decimal(value: object | None) -> Decimal:
    if value is None:
        return ZERO
    return Decimal(str(value)).quantize(FOUR_PLACES, rounding=ROUND_HALF_UP)


def _ratio_percent(part: object | None, total: object | None) -> Decimal:
    numerator = Decimal(str(part or 0))
    denominator = Decimal(str(total or 0))
    if denominator == 0:
        return ZERO
    return ((numerator / denominator) * 100).quantize(FOUR_PLACES, rounding=ROUND_HALF_UP)


def _average(total: object | None, count: int) -> Decimal:
    if count == 0:
        return ZERO
    return (Decimal(str(total or 0)) / Decimal(count)).quantize(FOUR_PLACES, rounding=ROUND_HALF_UP)


class AnalyticsService:
    """SQL-first deterministic analytics over normalized purchase-order facts."""

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _conditions(filters: AnalyticsFilters) -> list[object]:
        conditions: list[object] = []
        if filters.date_from is not None:
            conditions.append(PurchaseOrder.order_date >= filters.date_from)
        if filters.date_to is not None:
            conditions.append(PurchaseOrder.order_date <= filters.date_to)
        if filters.supplier_id is not None:
            conditions.append(PurchaseOrder.supplier_id == filters.supplier_id)
        if filters.category_id is not None:
            category_items = select(Item.item_id).where(Item.category_id == filters.category_id)
            conditions.append(PurchaseOrder.item_id.in_(category_items))
        if filters.business_unit_id is not None:
            conditions.append(PurchaseOrder.business_unit_id == filters.business_unit_id)
        if filters.country is not None:
            country_suppliers = select(Supplier.supplier_id).where(
                Supplier.supplier_country == filters.country
            )
            conditions.append(PurchaseOrder.supplier_id.in_(country_suppliers))
        return conditions

    def dashboard_summary(self, filters: AnalyticsFilters) -> DashboardSummary:
        statement = (
            select(
                func.coalesce(func.sum(PurchaseOrder.line_total), 0).label("total_spend"),
                func.count(PurchaseOrder.po_id).label("total_orders"),
                func.count(func.distinct(PurchaseOrder.supplier_id)).label("supplier_count"),
                func.count(func.distinct(Item.category_id)).label("category_count"),
                func.count(func.distinct(PurchaseOrder.business_unit_id)).label(
                    "business_unit_count"
                ),
            )
            .select_from(PurchaseOrder)
            .join(Item, PurchaseOrder.item_id == Item.item_id)
            .where(*self._conditions(filters))
        )
        row = self.session.execute(statement).one()
        total_orders = int(row.total_orders)
        return DashboardSummary(
            total_spend=_decimal(row.total_spend),
            total_orders=total_orders,
            average_order_value=_average(row.total_spend, total_orders),
            supplier_count=int(row.supplier_count),
            category_count=int(row.category_count),
            business_unit_count=int(row.business_unit_count),
        )

    def supplier_analytics(self, filters: AnalyticsFilters) -> list[SupplierAnalyticsItem]:
        spend = func.sum(PurchaseOrder.line_total).label("spend")
        statement = (
            select(
                Supplier.supplier_id,
                Supplier.supplier_name,
                Supplier.supplier_country,
                spend,
                func.count(PurchaseOrder.po_id).label("transaction_count"),
                func.sum(PurchaseOrder.quantity).label("total_quantity"),
            )
            .select_from(PurchaseOrder)
            .join(Supplier, PurchaseOrder.supplier_id == Supplier.supplier_id)
            .where(*self._conditions(filters))
            .group_by(
                Supplier.supplier_id,
                Supplier.supplier_name,
                Supplier.supplier_country,
            )
            .order_by(spend.desc(), Supplier.supplier_id)
        )
        rows = self.session.execute(statement).all()
        total_spend = sum((Decimal(str(row.spend)) for row in rows), start=Decimal(0))
        return [
            SupplierAnalyticsItem(
                supplier_id=row.supplier_id,
                supplier_name=row.supplier_name,
                country=row.supplier_country,
                spend=_decimal(row.spend),
                share_percent=_ratio_percent(row.spend, total_spend),
                transaction_count=int(row.transaction_count),
                average_order_value=_average(row.spend, int(row.transaction_count)),
                total_quantity=_decimal(row.total_quantity),
                rank=rank,
            )
            for rank, row in enumerate(rows, start=1)
        ]

    def supplier_concentration(self, filters: AnalyticsFilters) -> SupplierConcentration:
        grouped = (
            select(
                PurchaseOrder.supplier_id.label("supplier_id"),
                func.sum(PurchaseOrder.line_total).label("spend"),
            )
            .where(*self._conditions(filters))
            .group_by(PurchaseOrder.supplier_id)
            .cte("supplier_spend")
        )
        ranked = select(
            grouped.c.supplier_id,
            grouped.c.spend,
            func.row_number()
            .over(order_by=(grouped.c.spend.desc(), grouped.c.supplier_id))
            .label("rank"),
        ).cte("ranked_supplier_spend")
        statement = select(
            func.coalesce(func.sum(ranked.c.spend), 0).label("total_spend"),
            func.count(ranked.c.supplier_id).label("supplier_count"),
            func.coalesce(func.sum(case((ranked.c.rank <= 5, ranked.c.spend), else_=0)), 0).label(
                "top_5_spend"
            ),
            func.coalesce(func.sum(case((ranked.c.rank <= 10, ranked.c.spend), else_=0)), 0).label(
                "top_10_spend"
            ),
        )
        row = self.session.execute(statement).one()
        return SupplierConcentration(
            total_spend=_decimal(row.total_spend),
            supplier_count=int(row.supplier_count),
            top_5_spend=_decimal(row.top_5_spend),
            top_5_concentration_percent=_ratio_percent(row.top_5_spend, row.total_spend),
            top_10_spend=_decimal(row.top_10_spend),
            top_10_concentration_percent=_ratio_percent(row.top_10_spend, row.total_spend),
        )

    def category_analytics(self, filters: AnalyticsFilters) -> list[CategoryAnalyticsItem]:
        spend = func.sum(PurchaseOrder.line_total).label("spend")
        statement = (
            select(
                Category.category_id,
                Category.category_name,
                spend,
                func.count(PurchaseOrder.po_id).label("transaction_count"),
                func.count(func.distinct(PurchaseOrder.supplier_id)).label("supplier_count"),
            )
            .select_from(PurchaseOrder)
            .join(Item, PurchaseOrder.item_id == Item.item_id)
            .join(Category, Item.category_id == Category.category_id)
            .where(*self._conditions(filters))
            .group_by(Category.category_id, Category.category_name)
            .order_by(spend.desc(), Category.category_id)
        )
        rows = self.session.execute(statement).all()
        total_spend = sum((Decimal(str(row.spend)) for row in rows), start=Decimal(0))
        return [
            CategoryAnalyticsItem(
                category_id=int(row.category_id),
                category_name=row.category_name,
                spend=_decimal(row.spend),
                share_percent=_ratio_percent(row.spend, total_spend),
                transaction_count=int(row.transaction_count),
                average_order_value=_average(row.spend, int(row.transaction_count)),
                supplier_count=int(row.supplier_count),
            )
            for row in rows
        ]

    def business_unit_analytics(self, filters: AnalyticsFilters) -> list[BusinessUnitAnalyticsItem]:
        spend = func.sum(PurchaseOrder.line_total).label("spend")
        statement = (
            select(
                BusinessUnit.business_unit_id,
                BusinessUnit.business_unit_name,
                spend,
                func.count(PurchaseOrder.po_id).label("transaction_count"),
            )
            .select_from(PurchaseOrder)
            .join(
                BusinessUnit,
                PurchaseOrder.business_unit_id == BusinessUnit.business_unit_id,
            )
            .where(*self._conditions(filters))
            .group_by(BusinessUnit.business_unit_id, BusinessUnit.business_unit_name)
            .order_by(spend.desc(), BusinessUnit.business_unit_id)
        )
        rows = self.session.execute(statement).all()
        total_spend = sum((Decimal(str(row.spend)) for row in rows), start=Decimal(0))
        return [
            BusinessUnitAnalyticsItem(
                business_unit_id=int(row.business_unit_id),
                business_unit_name=row.business_unit_name,
                spend=_decimal(row.spend),
                share_percent=_ratio_percent(row.spend, total_spend),
                transaction_count=int(row.transaction_count),
            )
            for row in rows
        ]

    def monthly_analytics(self, filters: AnalyticsFilters) -> list[MonthlyAnalyticsItem]:
        year = cast(func.extract("year", PurchaseOrder.order_date), Integer).label("year")
        month = cast(func.extract("month", PurchaseOrder.order_date), Integer).label("month")
        spend = func.sum(PurchaseOrder.line_total).label("spend")
        statement = (
            select(
                year,
                month,
                spend,
                func.count(PurchaseOrder.po_id).label("transaction_count"),
            )
            .where(*self._conditions(filters))
            .group_by(year, month)
            .order_by(year, month)
        )
        rows = self.session.execute(statement).all()
        results: list[MonthlyAnalyticsItem] = []
        previous_spend: Decimal | None = None
        for row in rows:
            current_spend = Decimal(str(row.spend))
            growth = None
            if previous_spend is not None and previous_spend != 0:
                growth = _ratio_percent(current_spend - previous_spend, previous_spend)
            results.append(
                MonthlyAnalyticsItem(
                    month=date(int(row.year), int(row.month), 1),
                    spend=_decimal(current_spend),
                    transaction_count=int(row.transaction_count),
                    average_order_value=_average(current_spend, int(row.transaction_count)),
                    growth_percent=growth,
                )
            )
            previous_spend = current_spend
        return results

    def contract_analytics(self, filters: AnalyticsFilters) -> ContractAnalytics:
        on_contract_spend = func.coalesce(
            func.sum(
                case((PurchaseOrder.on_contract.is_(True), PurchaseOrder.line_total), else_=0)
            ),
            0,
        ).label("on_contract_spend")
        off_contract_spend = func.coalesce(
            func.sum(
                case((PurchaseOrder.on_contract.is_(False), PurchaseOrder.line_total), else_=0)
            ),
            0,
        ).label("off_contract_spend")
        statement = select(
            func.coalesce(func.sum(PurchaseOrder.line_total), 0).label("total_spend"),
            func.count(PurchaseOrder.po_id).label("total_orders"),
            on_contract_spend,
            off_contract_spend,
            func.sum(case((PurchaseOrder.on_contract.is_(True), 1), else_=0)).label(
                "on_contract_order_count"
            ),
            func.sum(case((PurchaseOrder.on_contract.is_(False), 1), else_=0)).label(
                "off_contract_order_count"
            ),
        ).where(*self._conditions(filters))
        row = self.session.execute(statement).one()
        return ContractAnalytics(
            total_spend=_decimal(row.total_spend),
            total_orders=int(row.total_orders),
            on_contract_spend=_decimal(row.on_contract_spend),
            off_contract_spend=_decimal(row.off_contract_spend),
            on_contract_percent=_ratio_percent(row.on_contract_spend, row.total_spend),
            off_contract_percent=_ratio_percent(row.off_contract_spend, row.total_spend),
            on_contract_order_count=int(row.on_contract_order_count or 0),
            off_contract_order_count=int(row.off_contract_order_count or 0),
        )

    def quality_analytics(self, filters: AnalyticsFilters) -> QualityAnalytics:
        rejected_count = func.sum(
            case((PurchaseOrder.quality_rejected.is_(True), 1), else_=0)
        ).label("rejected_count")
        rejected_spend = func.coalesce(
            func.sum(
                case(
                    (PurchaseOrder.quality_rejected.is_(True), PurchaseOrder.line_total),
                    else_=0,
                )
            ),
            0,
        ).label("rejected_spend")
        overall = self.session.execute(
            select(
                func.count(PurchaseOrder.po_id).label("total_orders"),
                rejected_count,
                rejected_spend,
            ).where(*self._conditions(filters))
        ).one()

        supplier_rows = self.session.execute(
            select(
                Supplier.supplier_id,
                Supplier.supplier_name,
                Supplier.supplier_country,
                func.count(PurchaseOrder.po_id).label("total_orders"),
                rejected_count,
                rejected_spend,
            )
            .select_from(PurchaseOrder)
            .join(Supplier, PurchaseOrder.supplier_id == Supplier.supplier_id)
            .where(*self._conditions(filters))
            .group_by(
                Supplier.supplier_id,
                Supplier.supplier_name,
                Supplier.supplier_country,
            )
        ).all()
        suppliers = [
            SupplierQualityMetric(
                supplier_id=row.supplier_id,
                supplier_name=row.supplier_name,
                country=row.supplier_country,
                total_orders=int(row.total_orders),
                rejected_order_count=int(row.rejected_count or 0),
                rejection_rate_percent=_ratio_percent(row.rejected_count, row.total_orders),
                rejected_spend=_decimal(row.rejected_spend),
            )
            for row in supplier_rows
        ]
        suppliers.sort(
            key=lambda item: (
                item.rejection_rate_percent,
                item.rejected_order_count,
                item.supplier_id,
            ),
            reverse=True,
        )
        return QualityAnalytics(
            total_orders=int(overall.total_orders),
            rejected_order_count=int(overall.rejected_count or 0),
            rejection_rate_percent=_ratio_percent(overall.rejected_count, overall.total_orders),
            rejected_spend=_decimal(overall.rejected_spend),
            suppliers=suppliers,
        )

    def delivery_analytics(self, filters: AnalyticsFilters) -> DeliveryAnalytics:
        late = PurchaseOrder.actual_delivery_date > PurchaseOrder.promised_delivery_date
        delay_days = DeliveryDelayDays(
            PurchaseOrder.actual_delivery_date, PurchaseOrder.promised_delivery_date
        )
        late_count = func.sum(case((late, 1), else_=0)).label("late_count")
        average_delay = func.avg(case((late, delay_days), else_=None)).label("average_delay")

        overall = self.session.execute(
            select(
                func.count(PurchaseOrder.po_id).label("total_orders"),
                late_count,
                average_delay,
            ).where(*self._conditions(filters))
        ).one()
        supplier_rows = self.session.execute(
            select(
                Supplier.supplier_id,
                Supplier.supplier_name,
                Supplier.supplier_country,
                func.count(PurchaseOrder.po_id).label("total_orders"),
                late_count,
                average_delay,
            )
            .select_from(PurchaseOrder)
            .join(Supplier, PurchaseOrder.supplier_id == Supplier.supplier_id)
            .where(*self._conditions(filters))
            .group_by(
                Supplier.supplier_id,
                Supplier.supplier_name,
                Supplier.supplier_country,
            )
        ).all()
        suppliers = [
            SupplierDeliveryMetric(
                supplier_id=row.supplier_id,
                supplier_name=row.supplier_name,
                country=row.supplier_country,
                total_orders=int(row.total_orders),
                late_order_count=int(row.late_count or 0),
                late_delivery_rate_percent=_ratio_percent(row.late_count, row.total_orders),
                average_delay_days=_decimal(row.average_delay),
            )
            for row in supplier_rows
        ]
        suppliers.sort(
            key=lambda item: (
                item.late_delivery_rate_percent,
                item.late_order_count,
                item.supplier_id,
            ),
            reverse=True,
        )
        return DeliveryAnalytics(
            total_orders=int(overall.total_orders),
            late_order_count=int(overall.late_count or 0),
            late_delivery_rate_percent=_ratio_percent(overall.late_count, overall.total_orders),
            average_delay_days=_decimal(overall.average_delay),
            suppliers=suppliers,
        )
