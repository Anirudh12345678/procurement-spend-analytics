from datetime import datetime
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Category, CostOpportunity, Item, ItemBenchmark, Supplier
from app.schemas.api import PaginatedResponse, PaginationParams
from app.schemas.optimization import (
    BenchmarkResponse,
    OpportunityResponse,
    OpportunitySummary,
)


class OptimizationQueryService:
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _benchmark_response(row) -> BenchmarkResponse:
        return BenchmarkResponse(
            benchmark_id=int(row.benchmark_id),
            item_id=int(row.item_id),
            item_name=row.item_name,
            category_id=int(row.category_id),
            category_name=row.category_name,
            benchmark_price=Decimal(row.benchmark_price),
            min_price=Decimal(row.min_price),
            max_price=Decimal(row.max_price),
            median_price=Decimal(row.median_price),
            p25_price=Decimal(row.p25_price),
            p75_price=Decimal(row.p75_price),
            supplier_count=int(row.supplier_count),
            total_quantity=Decimal(row.total_quantity),
            total_spend=Decimal(row.total_spend),
            calculated_at=row.calculated_at,
        )

    def benchmarks(
        self,
        pagination: PaginationParams,
        *,
        category_id: int | None = None,
        search: str | None = None,
    ) -> PaginatedResponse[BenchmarkResponse]:
        conditions = []
        if category_id is not None:
            conditions.append(Category.category_id == category_id)
        if search:
            conditions.append(Item.item_name.ilike(f"%{search}%"))
        base = (
            select(
                ItemBenchmark.benchmark_id,
                ItemBenchmark.item_id,
                Item.item_name,
                Category.category_id,
                Category.category_name,
                ItemBenchmark.benchmark_price,
                ItemBenchmark.min_price,
                ItemBenchmark.max_price,
                ItemBenchmark.median_price,
                ItemBenchmark.p25_price,
                ItemBenchmark.p75_price,
                ItemBenchmark.supplier_count,
                ItemBenchmark.total_quantity,
                ItemBenchmark.total_spend,
                ItemBenchmark.calculated_at,
            )
            .join(Item, ItemBenchmark.item_id == Item.item_id)
            .join(Category, Item.category_id == Category.category_id)
            .where(*conditions)
        )
        total = self.session.scalar(select(func.count()).select_from(base.subquery())) or 0
        rows = self.session.execute(
            base.order_by(ItemBenchmark.total_spend.desc(), Item.item_name)
            .offset(pagination.offset)
            .limit(pagination.page_size)
        ).all()
        return PaginatedResponse.create(
            items=[self._benchmark_response(row) for row in rows],
            total=int(total),
            pagination=pagination,
        )

    def benchmark(self, item_id: int) -> BenchmarkResponse | None:
        row = self.session.execute(
            select(
                ItemBenchmark.benchmark_id,
                ItemBenchmark.item_id,
                Item.item_name,
                Category.category_id,
                Category.category_name,
                ItemBenchmark.benchmark_price,
                ItemBenchmark.min_price,
                ItemBenchmark.max_price,
                ItemBenchmark.median_price,
                ItemBenchmark.p25_price,
                ItemBenchmark.p75_price,
                ItemBenchmark.supplier_count,
                ItemBenchmark.total_quantity,
                ItemBenchmark.total_spend,
                ItemBenchmark.calculated_at,
            )
            .join(Item, ItemBenchmark.item_id == Item.item_id)
            .join(Category, Item.category_id == Category.category_id)
            .where(ItemBenchmark.item_id == item_id)
        ).one_or_none()
        return self._benchmark_response(row) if row else None

    @staticmethod
    def _opportunity_response(row) -> OpportunityResponse:
        return OpportunityResponse(
            opportunity_id=int(row.opportunity_id),
            opportunity_type=row.opportunity_type,
            item_id=int(row.item_id),
            item_name=row.item_name,
            category_id=int(row.category_id),
            category_name=row.category_name,
            supplier_id=row.supplier_id,
            supplier_name=row.supplier_name,
            actual_price=Decimal(row.actual_price) if row.actual_price is not None else None,
            benchmark_price=(
                Decimal(row.benchmark_price) if row.benchmark_price is not None else None
            ),
            price_variance_percent=(
                Decimal(row.price_variance_percent)
                if row.price_variance_percent is not None
                else None
            ),
            quantity=Decimal(row.quantity) if row.quantity is not None else None,
            estimated_savings=Decimal(row.estimated_savings),
            review_spend=Decimal(row.review_spend),
            confidence_score=Decimal(row.confidence_score),
            priority_score=Decimal(row.priority_score),
            priority_level=row.priority_level,
            status=row.status,
            supporting_metrics=row.supporting_metrics or {},
            created_at=row.created_at,
        )

    @staticmethod
    def _opportunity_base():
        return (
            select(
                CostOpportunity.opportunity_id,
                CostOpportunity.opportunity_type,
                CostOpportunity.item_id,
                Item.item_name,
                Category.category_id,
                Category.category_name,
                CostOpportunity.supplier_id,
                Supplier.supplier_name,
                CostOpportunity.actual_price,
                CostOpportunity.benchmark_price,
                CostOpportunity.price_variance_percent,
                CostOpportunity.quantity,
                CostOpportunity.estimated_savings,
                CostOpportunity.review_spend,
                CostOpportunity.confidence_score,
                CostOpportunity.priority_score,
                CostOpportunity.priority_level,
                CostOpportunity.status,
                CostOpportunity.supporting_metrics,
                CostOpportunity.created_at,
            )
            .join(Item, CostOpportunity.item_id == Item.item_id)
            .join(Category, Item.category_id == Category.category_id)
            .outerjoin(Supplier, CostOpportunity.supplier_id == Supplier.supplier_id)
        )

    def opportunities(
        self,
        pagination: PaginationParams,
        *,
        opportunity_type: str | None = None,
        priority: str | None = None,
        supplier_id: str | None = None,
        category_id: int | None = None,
        item_id: int | None = None,
        status: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        sort_by: str = "priority_score",
        sort_direction: str = "desc",
    ) -> PaginatedResponse[OpportunityResponse]:
        conditions = []
        if opportunity_type:
            conditions.append(CostOpportunity.opportunity_type == opportunity_type)
        if priority:
            conditions.append(CostOpportunity.priority_level == priority)
        if supplier_id:
            conditions.append(CostOpportunity.supplier_id == supplier_id)
        if category_id is not None:
            conditions.append(Category.category_id == category_id)
        if item_id is not None:
            conditions.append(CostOpportunity.item_id == item_id)
        conditions.append(CostOpportunity.status == (status or "OPEN"))
        if created_from:
            conditions.append(CostOpportunity.created_at >= created_from)
        if created_to:
            conditions.append(CostOpportunity.created_at <= created_to)
        base = self._opportunity_base().where(*conditions)
        total = self.session.scalar(select(func.count()).select_from(base.subquery())) or 0
        sort_columns = {
            "priority_score": CostOpportunity.priority_score,
            "estimated_savings": CostOpportunity.estimated_savings,
            "review_spend": CostOpportunity.review_spend,
            "created_at": CostOpportunity.created_at,
        }
        sort_column = sort_columns[sort_by]
        ordering = sort_column.desc() if sort_direction == "desc" else sort_column.asc()
        rows = self.session.execute(
            base.order_by(ordering, CostOpportunity.opportunity_id)
            .offset(pagination.offset)
            .limit(pagination.page_size)
        ).all()
        return PaginatedResponse.create(
            items=[self._opportunity_response(row) for row in rows],
            total=int(total),
            pagination=pagination,
        )

    def opportunity(self, opportunity_id: int) -> OpportunityResponse | None:
        row = self.session.execute(
            self._opportunity_base().where(CostOpportunity.opportunity_id == opportunity_id)
        ).one_or_none()
        return self._opportunity_response(row) if row else None

    def summary(self) -> OpportunitySummary:
        active = CostOpportunity.status == "OPEN"
        row = self.session.execute(
            select(
                func.sum(case((active, 1), else_=0)).label("count"),
                func.sum(
                    case(
                        (
                            active & (CostOpportunity.opportunity_type == "PRICE_OPTIMIZATION"),
                            CostOpportunity.estimated_savings,
                        ),
                        else_=0,
                    )
                ).label("estimated_savings"),
                func.sum(case((active, CostOpportunity.review_spend), else_=0)).label(
                    "review_spend"
                ),
                func.sum(
                    case((active & (CostOpportunity.priority_level == "CRITICAL"), 1), else_=0)
                ).label("critical"),
                func.sum(
                    case((active & (CostOpportunity.priority_level == "HIGH"), 1), else_=0)
                ).label("high"),
                *[
                    func.sum(
                        case(
                            (active & (CostOpportunity.opportunity_type == opportunity_type), 1),
                            else_=0,
                        )
                    ).label(opportunity_type.lower())
                    for opportunity_type in CostOpportunity.OPPORTUNITY_TYPES
                ],
            )
        ).one()
        return OpportunitySummary(
            active_opportunity_count=int(row.count or 0),
            estimated_price_optimization_savings=Decimal(row.estimated_savings or 0),
            review_spend=Decimal(row.review_spend or 0),
            critical_count=int(row.critical or 0),
            high_priority_count=int(row.high or 0),
            price_optimization_count=int(row.price_optimization or 0),
            contract_leakage_count=int(row.contract_leakage or 0),
            supplier_consolidation_count=int(row.supplier_consolidation or 0),
            supplier_performance_count=int(row.supplier_performance or 0),
            savings_note=(
                "Only non-overlapping price-optimization estimates are summed. Other opportunity "
                "types are review spend and are not additive or guaranteed savings."
            ),
        )
