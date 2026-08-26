import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import BusinessUnit, CostOpportunity, ItemBenchmark, PurchaseOrder
from app.optimization.config import OptimizationConfig
from app.optimization.formulas import (
    confidence_score,
    percentile_cont,
    potential_savings,
    price_variance_percent,
    priority_score,
    quantize,
    supplier_performance_score,
)

logger = logging.getLogger(__name__)
ZERO = Decimal("0")
HUNDRED = Decimal("100")


@dataclass(frozen=True)
class SupplierItemAggregate:
    item_id: int
    supplier_id: str
    weighted_price: Decimal
    quantity: Decimal
    spend: Decimal
    transaction_count: int


@dataclass(frozen=True)
class OpportunityCandidate:
    opportunity_type: str
    item_id: int
    supplier_id: str | None
    actual_price: Decimal | None
    benchmark_price: Decimal | None
    price_variance_percent: Decimal | None
    quantity: Decimal | None
    estimated_savings: Decimal
    review_spend: Decimal
    confidence_score: Decimal
    priority_score: Decimal
    priority_level: str
    supporting_metrics: dict[str, object]


def _json_decimal(value: Decimal) -> str:
    return str(quantize(value))


class OptimizationEngine:
    """Deterministic benchmark and procurement opportunity engine."""

    def __init__(self, session: Session, config: OptimizationConfig | None = None):
        self.session = session
        self.config = config or OptimizationConfig.from_settings(get_settings())

    def _supplier_item_aggregates(self) -> list[SupplierItemAggregate]:
        rows = self.session.execute(
            select(
                PurchaseOrder.item_id,
                PurchaseOrder.supplier_id,
                func.sum(PurchaseOrder.line_total).label("spend"),
                func.sum(PurchaseOrder.quantity).label("quantity"),
                func.count(PurchaseOrder.po_id).label("transaction_count"),
            )
            .group_by(PurchaseOrder.item_id, PurchaseOrder.supplier_id)
            .order_by(PurchaseOrder.item_id, PurchaseOrder.supplier_id)
        ).all()
        return [
            SupplierItemAggregate(
                item_id=int(row.item_id),
                supplier_id=row.supplier_id,
                weighted_price=quantize(Decimal(row.spend) / Decimal(row.quantity)),
                quantity=Decimal(row.quantity),
                spend=Decimal(row.spend),
                transaction_count=int(row.transaction_count),
            )
            for row in rows
        ]

    def calculate_benchmarks(
        self, aggregates: list[SupplierItemAggregate] | None = None
    ) -> list[ItemBenchmark]:
        aggregates = aggregates or self._supplier_item_aggregates()
        grouped: dict[int, list[SupplierItemAggregate]] = defaultdict(list)
        for aggregate in aggregates:
            grouped[aggregate.item_id].append(aggregate)

        existing = {
            benchmark.item_id: benchmark
            for benchmark in self.session.scalars(select(ItemBenchmark))
        }
        calculated: list[ItemBenchmark] = []
        now = datetime.now(UTC)
        for item_id, item_rows in grouped.items():
            prices = [row.weighted_price for row in item_rows]
            values = {
                "benchmark_price": percentile_cont(prices, Decimal("0.25")),
                "min_price": quantize(min(prices)),
                "max_price": quantize(max(prices)),
                "median_price": percentile_cont(prices, Decimal("0.50")),
                "p25_price": percentile_cont(prices, Decimal("0.25")),
                "p75_price": percentile_cont(prices, Decimal("0.75")),
                "supplier_count": len(item_rows),
                "total_quantity": quantize(sum((row.quantity for row in item_rows), start=ZERO)),
                "total_spend": quantize(sum((row.spend for row in item_rows), start=ZERO)),
                "calculated_at": now,
            }
            benchmark = existing.get(item_id)
            if benchmark is None:
                benchmark = ItemBenchmark(item_id=item_id, **values)
                self.session.add(benchmark)
            else:
                for field, value in values.items():
                    setattr(benchmark, field, value)
            calculated.append(benchmark)
        self.session.flush()
        logger.info("Calculated and stored %s item benchmarks", len(calculated))
        return calculated

    def _supplier_stats(self) -> dict[str, dict[str, Decimal | int]]:
        late = PurchaseOrder.actual_delivery_date > PurchaseOrder.promised_delivery_date
        rows = self.session.execute(
            select(
                PurchaseOrder.supplier_id,
                func.sum(PurchaseOrder.line_total).label("spend"),
                func.count(PurchaseOrder.po_id).label("orders"),
                func.sum(case((PurchaseOrder.quality_rejected.is_(True), 1), else_=0)).label(
                    "rejected"
                ),
                func.sum(case((late, 1), else_=0)).label("late"),
                func.sum(
                    case(
                        (PurchaseOrder.on_contract.is_(True), PurchaseOrder.line_total),
                        else_=0,
                    )
                ).label("on_contract_spend"),
            ).group_by(PurchaseOrder.supplier_id)
        ).all()
        return {
            row.supplier_id: {
                "spend": Decimal(row.spend),
                "orders": int(row.orders),
                "rejected": int(row.rejected or 0),
                "late": int(row.late or 0),
                "on_contract_spend": Decimal(row.on_contract_spend or 0),
            }
            for row in rows
        }

    def _price_opportunities(
        self,
        aggregates: list[SupplierItemAggregate],
        benchmarks: dict[int, ItemBenchmark],
        supplier_stats: dict[str, dict[str, Decimal | int]],
    ) -> list[OpportunityCandidate]:
        candidates: list[OpportunityCandidate] = []
        for aggregate in aggregates:
            benchmark = benchmarks[aggregate.item_id]
            if benchmark.supplier_count < self.config.min_benchmark_suppliers:
                continue
            variance = price_variance_percent(
                aggregate.weighted_price, Decimal(benchmark.benchmark_price)
            )
            savings = potential_savings(
                aggregate.weighted_price,
                Decimal(benchmark.benchmark_price),
                aggregate.quantity,
            )
            if variance < self.config.price_variance_threshold_percent:
                continue
            if savings < self.config.min_price_opportunity_savings:
                continue
            confidence = confidence_score(
                supplier_count=benchmark.supplier_count,
                transaction_count=aggregate.transaction_count,
                quantity=aggregate.quantity,
                median_price=Decimal(benchmark.median_price),
                p25_price=Decimal(benchmark.p25_price),
                p75_price=Decimal(benchmark.p75_price),
            )
            priority, level = priority_score(
                financial_impact=savings,
                confidence=confidence,
                severity=min(variance / Decimal("50"), Decimal(1)),
                config=self.config,
            )
            stats = supplier_stats[aggregate.supplier_id]
            orders = Decimal(int(stats["orders"]))
            candidates.append(
                OpportunityCandidate(
                    opportunity_type="PRICE_OPTIMIZATION",
                    item_id=aggregate.item_id,
                    supplier_id=aggregate.supplier_id,
                    actual_price=aggregate.weighted_price,
                    benchmark_price=Decimal(benchmark.benchmark_price),
                    price_variance_percent=variance,
                    quantity=aggregate.quantity,
                    estimated_savings=savings,
                    review_spend=aggregate.spend,
                    confidence_score=confidence,
                    priority_score=priority,
                    priority_level=level,
                    supporting_metrics={
                        "transaction_count": aggregate.transaction_count,
                        "supplier_count": benchmark.supplier_count,
                        "supplier_rejection_rate": _json_decimal(
                            Decimal(int(stats["rejected"])) / orders
                        ),
                        "supplier_late_delivery_rate": _json_decimal(
                            Decimal(int(stats["late"])) / orders
                        ),
                        "supplier_contract_compliance_rate": _json_decimal(
                            Decimal(stats["on_contract_spend"]) / Decimal(stats["spend"])
                        ),
                        "method": "supplier quantity-weighted average versus item p25 benchmark",
                    },
                )
            )
        return candidates

    def _contract_leakage_opportunities(
        self, supplier_stats: dict[str, dict[str, Decimal | int]]
    ) -> list[OpportunityCandidate]:
        off_spend = func.sum(
            case((PurchaseOrder.on_contract.is_(False), PurchaseOrder.line_total), else_=0)
        )
        off_quantity = func.sum(
            case((PurchaseOrder.on_contract.is_(False), PurchaseOrder.quantity), else_=0)
        )
        off_orders = func.sum(case((PurchaseOrder.on_contract.is_(False), 1), else_=0))
        rows = self.session.execute(
            select(
                PurchaseOrder.item_id,
                PurchaseOrder.supplier_id,
                func.sum(PurchaseOrder.line_total).label("total_spend"),
                off_spend.label("off_spend"),
                off_quantity.label("off_quantity"),
                off_orders.label("off_orders"),
            )
            .group_by(PurchaseOrder.item_id, PurchaseOrder.supplier_id)
            .having(off_spend >= self.config.contract_leakage_min_spend)
        ).all()

        top_unit_rows = self.session.execute(
            select(
                PurchaseOrder.item_id,
                PurchaseOrder.supplier_id,
                BusinessUnit.business_unit_name,
                off_spend.label("off_spend"),
            )
            .join(BusinessUnit, PurchaseOrder.business_unit_id == BusinessUnit.business_unit_id)
            .where(PurchaseOrder.on_contract.is_(False))
            .group_by(
                PurchaseOrder.item_id,
                PurchaseOrder.supplier_id,
                BusinessUnit.business_unit_name,
            )
        ).all()
        top_units: dict[tuple[int, str], tuple[str, Decimal]] = {}
        for row in top_unit_rows:
            key = (int(row.item_id), row.supplier_id)
            value = (row.business_unit_name, Decimal(row.off_spend))
            if key not in top_units or value[1] > top_units[key][1]:
                top_units[key] = value

        candidates: list[OpportunityCandidate] = []
        for row in rows:
            spend = Decimal(row.off_spend)
            total_spend = Decimal(row.total_spend)
            off_orders_value = int(row.off_orders or 0)
            leakage_rate = spend / total_spend if total_spend else ZERO
            confidence = quantize(
                min(Decimal(off_orders_value) / Decimal(20), Decimal(1)) * Decimal("0.55")
                + min(spend / self.config.priority_high_impact_amount, Decimal(1)) * Decimal("0.45")
            )
            priority, level = priority_score(
                financial_impact=spend,
                confidence=confidence,
                severity=leakage_rate,
                config=self.config,
            )
            top_unit, top_unit_spend = top_units[(int(row.item_id), row.supplier_id)]
            supplier_total = Decimal(supplier_stats[row.supplier_id]["spend"])
            candidates.append(
                OpportunityCandidate(
                    opportunity_type="CONTRACT_LEAKAGE",
                    item_id=int(row.item_id),
                    supplier_id=row.supplier_id,
                    actual_price=None,
                    benchmark_price=None,
                    price_variance_percent=None,
                    quantity=Decimal(row.off_quantity),
                    estimated_savings=ZERO,
                    review_spend=spend,
                    confidence_score=confidence,
                    priority_score=priority,
                    priority_level=level,
                    supporting_metrics={
                        "off_contract_order_count": off_orders_value,
                        "off_contract_spend_rate": _json_decimal(leakage_rate),
                        "supplier_off_contract_spend": _json_decimal(
                            supplier_total
                            - Decimal(supplier_stats[row.supplier_id]["on_contract_spend"])
                        ),
                        "top_business_unit": top_unit,
                        "top_business_unit_off_contract_spend": _json_decimal(top_unit_spend),
                        "method": (
                            "material off-contract spend requiring procurement review; not savings"
                        ),
                    },
                )
            )
        return candidates

    def _consolidation_opportunities(
        self,
        aggregates: list[SupplierItemAggregate],
        benchmarks: dict[int, ItemBenchmark],
    ) -> list[OpportunityCandidate]:
        transaction_counts: dict[int, int] = defaultdict(int)
        for aggregate in aggregates:
            transaction_counts[aggregate.item_id] += aggregate.transaction_count
        candidates: list[OpportunityCandidate] = []
        for item_id, benchmark in benchmarks.items():
            median = Decimal(benchmark.median_price)
            dispersion = (
                price_variance_percent(Decimal(benchmark.p75_price), Decimal(benchmark.p25_price))
                if Decimal(benchmark.p25_price) > 0
                else ZERO
            )
            if benchmark.supplier_count < self.config.consolidation_min_suppliers:
                continue
            if Decimal(benchmark.total_spend) < self.config.consolidation_min_spend:
                continue
            if dispersion < self.config.consolidation_min_dispersion_percent:
                continue
            confidence = confidence_score(
                supplier_count=benchmark.supplier_count,
                transaction_count=transaction_counts[item_id],
                quantity=Decimal(benchmark.total_quantity),
                median_price=median,
                p25_price=Decimal(benchmark.p25_price),
                p75_price=Decimal(benchmark.p75_price),
            )
            severity = min(dispersion / Decimal("50"), Decimal(1))
            priority, level = priority_score(
                financial_impact=Decimal(benchmark.total_spend),
                confidence=confidence,
                severity=severity,
                config=self.config,
            )
            candidates.append(
                OpportunityCandidate(
                    opportunity_type="SUPPLIER_CONSOLIDATION",
                    item_id=item_id,
                    supplier_id=None,
                    actual_price=Decimal(benchmark.p75_price),
                    benchmark_price=Decimal(benchmark.p25_price),
                    price_variance_percent=dispersion,
                    quantity=Decimal(benchmark.total_quantity),
                    estimated_savings=ZERO,
                    review_spend=Decimal(benchmark.total_spend),
                    confidence_score=confidence,
                    priority_score=priority,
                    priority_level=level,
                    supporting_metrics={
                        "supplier_count": benchmark.supplier_count,
                        "transaction_count": transaction_counts[item_id],
                        "median_price": _json_decimal(median),
                        "p25_p75_dispersion_percent": _json_decimal(dispersion),
                        "method": "evaluate supplier consolidation or volume-based negotiation",
                    },
                )
            )
        return candidates

    def _supplier_performance_opportunities(
        self,
        aggregates: list[SupplierItemAggregate],
        benchmarks: dict[int, ItemBenchmark],
        supplier_stats: dict[str, dict[str, Decimal | int]],
    ) -> list[OpportunityCandidate]:
        grouped: dict[str, list[SupplierItemAggregate]] = defaultdict(list)
        for aggregate in aggregates:
            grouped[aggregate.supplier_id].append(aggregate)
        candidates: list[OpportunityCandidate] = []
        for supplier_id, supplier_rows in grouped.items():
            stats = supplier_stats[supplier_id]
            spend = Decimal(stats["spend"])
            if spend < self.config.supplier_performance_min_spend:
                continue
            benchmarked_rows = [row for row in supplier_rows if row.item_id in benchmarks]
            benchmarked_spend = sum((row.spend for row in benchmarked_rows), start=ZERO)
            price_points = ZERO
            for row in benchmarked_rows:
                variance = price_variance_percent(
                    row.weighted_price, Decimal(benchmarks[row.item_id].benchmark_price)
                )
                component_score = max(ZERO, HUNDRED - max(ZERO, variance))
                price_points += component_score * row.spend
            price_score = price_points / benchmarked_spend if benchmarked_spend else Decimal("50")
            order_count = Decimal(int(stats["orders"]))
            score, components = supplier_performance_score(
                price_score=price_score,
                rejection_rate=Decimal(int(stats["rejected"])) / order_count,
                late_delivery_rate=Decimal(int(stats["late"])) / order_count,
                contract_compliance_rate=Decimal(stats["on_contract_spend"]) / spend,
                config=self.config,
            )
            if score >= self.config.supplier_performance_score_threshold:
                continue
            representative = max(supplier_rows, key=lambda row: row.spend)
            coverage = benchmarked_spend / spend if spend else ZERO
            confidence = quantize(
                min(order_count / Decimal(100), Decimal(1)) * Decimal("0.50")
                + min(coverage, Decimal(1)) * Decimal("0.50")
            )
            severity = max(ZERO, (HUNDRED - score) / HUNDRED)
            priority, level = priority_score(
                financial_impact=spend,
                confidence=confidence,
                severity=severity,
                config=self.config,
            )
            candidates.append(
                OpportunityCandidate(
                    opportunity_type="SUPPLIER_PERFORMANCE",
                    item_id=representative.item_id,
                    supplier_id=supplier_id,
                    actual_price=None,
                    benchmark_price=None,
                    price_variance_percent=None,
                    quantity=None,
                    estimated_savings=ZERO,
                    review_spend=spend,
                    confidence_score=confidence,
                    priority_score=priority,
                    priority_level=level,
                    supporting_metrics={
                        "supplier_score": _json_decimal(score),
                        "price_score": _json_decimal(components["price_score"]),
                        "quality_score": _json_decimal(components["quality_score"]),
                        "delivery_score": _json_decimal(components["delivery_score"]),
                        "contract_score": _json_decimal(components["contract_score"]),
                        "quality_rejection_rate": _json_decimal(
                            Decimal(int(stats["rejected"])) / order_count
                        ),
                        "late_delivery_rate": _json_decimal(
                            Decimal(int(stats["late"])) / order_count
                        ),
                        "contract_compliance_rate": _json_decimal(
                            Decimal(stats["on_contract_spend"]) / spend
                        ),
                        "benchmark_coverage_rate": _json_decimal(coverage),
                        "method": "configurable 40/25/20/15 price-quality-delivery-contract score",
                    },
                )
            )
        return candidates

    def calculate_opportunities(
        self,
        aggregates: list[SupplierItemAggregate] | None = None,
        benchmark_rows: list[ItemBenchmark] | None = None,
    ) -> list[CostOpportunity]:
        aggregates = aggregates or self._supplier_item_aggregates()
        benchmark_rows = benchmark_rows or list(self.session.scalars(select(ItemBenchmark)))
        benchmarks = {row.item_id: row for row in benchmark_rows}
        supplier_stats = self._supplier_stats()
        candidates = [
            *self._price_opportunities(aggregates, benchmarks, supplier_stats),
            *self._contract_leakage_opportunities(supplier_stats),
            *self._consolidation_opportunities(aggregates, benchmarks),
            *self._supplier_performance_opportunities(aggregates, benchmarks, supplier_stats),
        ]

        existing = {
            (row.opportunity_type, row.item_id, row.supplier_id): row
            for row in self.session.scalars(select(CostOpportunity))
        }
        active_keys: set[tuple[str, int, str | None]] = set()
        results: list[CostOpportunity] = []
        for candidate in candidates:
            key = (candidate.opportunity_type, candidate.item_id, candidate.supplier_id)
            active_keys.add(key)
            opportunity = existing.get(key)
            values = {
                "actual_price": candidate.actual_price,
                "benchmark_price": candidate.benchmark_price,
                "price_variance_percent": candidate.price_variance_percent,
                "quantity": candidate.quantity,
                "estimated_savings": candidate.estimated_savings,
                "review_spend": candidate.review_spend,
                "confidence_score": candidate.confidence_score,
                "priority_score": candidate.priority_score,
                "priority_level": candidate.priority_level,
                "supporting_metrics": candidate.supporting_metrics,
            }
            if opportunity is None:
                opportunity = CostOpportunity(
                    opportunity_type=candidate.opportunity_type,
                    item_id=candidate.item_id,
                    supplier_id=candidate.supplier_id,
                    status="OPEN",
                    **values,
                )
                self.session.add(opportunity)
            else:
                for field, value in values.items():
                    setattr(opportunity, field, value)
                if opportunity.status == "STALE":
                    opportunity.status = "OPEN"
            results.append(opportunity)

        for key, opportunity in existing.items():
            if key not in active_keys:
                opportunity.status = "STALE"
        self.session.flush()
        logger.info(
            "Calculated %s active opportunities: %s",
            len(results),
            {
                opportunity_type: sum(
                    1 for item in results if item.opportunity_type == opportunity_type
                )
                for opportunity_type in CostOpportunity.OPPORTUNITY_TYPES
            },
        )
        return results

    def run(self) -> tuple[list[ItemBenchmark], list[CostOpportunity]]:
        aggregates = self._supplier_item_aggregates()
        benchmarks = self.calculate_benchmarks(aggregates)
        opportunities = self.calculate_opportunities(aggregates, benchmarks)
        return benchmarks, opportunities
