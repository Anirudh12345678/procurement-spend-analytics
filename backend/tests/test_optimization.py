from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CostOpportunity, ItemBenchmark
from app.optimization.config import OptimizationConfig
from app.optimization.engine import OptimizationEngine
from app.optimization.formulas import (
    confidence_score,
    percentile_cont,
    potential_savings,
    price_variance_percent,
    priority_score,
    quantity_weighted_average_price,
    supplier_performance_score,
)


def optimization_config(**overrides) -> OptimizationConfig:
    values = {
        "price_variance_threshold_percent": Decimal("10"),
        "min_price_opportunity_savings": Decimal("5"),
        "min_benchmark_suppliers": 2,
        "contract_leakage_min_spend": Decimal("50"),
        "consolidation_min_spend": Decimal("100"),
        "consolidation_min_suppliers": 2,
        "consolidation_min_dispersion_percent": Decimal("10"),
        "supplier_performance_min_spend": Decimal("50"),
        "supplier_performance_score_threshold": Decimal("95"),
        "supplier_score_price_weight": Decimal("0.40"),
        "supplier_score_quality_weight": Decimal("0.25"),
        "supplier_score_delivery_weight": Decimal("0.20"),
        "supplier_score_contract_weight": Decimal("0.15"),
        "priority_impact_weight": Decimal("0.50"),
        "priority_confidence_weight": Decimal("0.30"),
        "priority_severity_weight": Decimal("0.20"),
        "priority_high_impact_amount": Decimal("1000"),
    }
    values.update(overrides)
    return OptimizationConfig(**values)


def test_quantity_weighted_supplier_price() -> None:
    result = quantity_weighted_average_price(
        [(Decimal("10"), Decimal("1")), (Decimal("20"), Decimal("3"))]
    )
    assert result == Decimal("17.5000")


def test_continuous_p25_uses_supplier_level_distribution() -> None:
    result = percentile_cont(
        [Decimal("17.5"), Decimal("30"), Decimal("40"), Decimal("50")],
        Decimal("0.25"),
    )
    assert result == Decimal("26.8750")


def test_price_variance_and_potential_savings() -> None:
    assert price_variance_percent(Decimal("82.50"), Decimal("61.20")) == Decimal("34.8039")
    assert potential_savings(Decimal("82.50"), Decimal("61.20"), Decimal("4200")) == Decimal(
        "89460.0000"
    )
    assert potential_savings(Decimal("50"), Decimal("60"), Decimal("100")) == Decimal("0.0000")


def test_confidence_score_is_bounded_and_explainable() -> None:
    sparse = confidence_score(
        supplier_count=2,
        transaction_count=2,
        quantity=Decimal("10"),
        median_price=Decimal("100"),
        p25_price=Decimal("70"),
        p75_price=Decimal("130"),
    )
    robust = confidence_score(
        supplier_count=6,
        transaction_count=30,
        quantity=Decimal("10000"),
        median_price=Decimal("100"),
        p25_price=Decimal("95"),
        p75_price=Decimal("105"),
    )
    assert Decimal(0) <= sparse <= Decimal(1)
    assert Decimal(0) <= robust <= Decimal(1)
    assert robust > sparse


def test_supplier_score_uses_configured_weights() -> None:
    score, components = supplier_performance_score(
        price_score=Decimal("70"),
        rejection_rate=Decimal("0.04"),
        late_delivery_rate=Decimal("0.10"),
        contract_compliance_rate=Decimal("0.80"),
        config=optimization_config(),
    )
    assert components == {
        "price_score": Decimal("70.0000"),
        "quality_score": Decimal("96.0000"),
        "delivery_score": Decimal("90.0000"),
        "contract_score": Decimal("80.0000"),
    }
    assert score == Decimal("82.0000")


def test_priority_formula_and_levels() -> None:
    score, level = priority_score(
        financial_impact=Decimal("1000"),
        confidence=Decimal("0.9"),
        severity=Decimal("0.8"),
        config=optimization_config(),
    )
    assert score == Decimal("93.0000")
    assert level == "CRITICAL"


def test_engine_stores_benchmarks_and_distinct_opportunity_types(
    analytics_session: Session,
) -> None:
    engine = OptimizationEngine(
        analytics_session,
        optimization_config(
            price_variance_threshold_percent=Decimal("5"),
            min_price_opportunity_savings=Decimal("1"),
            supplier_performance_score_threshold=Decimal("100"),
        ),
    )
    benchmarks, opportunities = engine.run()

    assert len(benchmarks) == 2
    assert analytics_session.scalar(select(ItemBenchmark).limit(1)) is not None
    types = {opportunity.opportunity_type for opportunity in opportunities}
    assert "PRICE_OPTIMIZATION" in types
    assert "CONTRACT_LEAKAGE" in types
    assert "SUPPLIER_CONSOLIDATION" in types
    assert "SUPPLIER_PERFORMANCE" in types
    contract = next(item for item in opportunities if item.opportunity_type == "CONTRACT_LEAKAGE")
    assert contract.estimated_savings == Decimal("0")
    assert contract.review_spend > 0
    assert "not savings" in str(contract.supporting_metrics["method"])


def test_optimization_engine_is_rerunnable_without_duplicates(
    analytics_session: Session,
) -> None:
    engine = OptimizationEngine(analytics_session, optimization_config())
    first_benchmarks, first_opportunities = engine.run()
    first_count = len(first_opportunities)
    second_benchmarks, second_opportunities = engine.run()

    assert len(first_benchmarks) == len(second_benchmarks)
    assert len(second_opportunities) == first_count
    assert len(list(analytics_session.scalars(select(CostOpportunity)))) == first_count
