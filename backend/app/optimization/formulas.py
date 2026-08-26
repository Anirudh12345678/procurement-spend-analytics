from decimal import ROUND_HALF_UP, Decimal
from math import ceil, floor, log10

from app.optimization.config import OptimizationConfig

FOUR_PLACES = Decimal("0.0001")
TWO_PLACES = Decimal("0.01")
HUNDRED = Decimal("100")
ZERO = Decimal("0")
ONE = Decimal("1")


def quantize(value: Decimal) -> Decimal:
    return value.quantize(FOUR_PLACES, rounding=ROUND_HALF_UP)


def quantity_weighted_average_price(values: list[tuple[Decimal, Decimal]]) -> Decimal:
    total_quantity = sum((quantity for _, quantity in values), start=ZERO)
    if total_quantity <= 0:
        raise ValueError("total quantity must be positive")
    total_value = sum((price * quantity for price, quantity in values), start=ZERO)
    return quantize(total_value / total_quantity)


def percentile_cont(values: list[Decimal], percentile: Decimal) -> Decimal:
    if not values:
        raise ValueError("at least one value is required")
    if percentile < 0 or percentile > 1:
        raise ValueError("percentile must be between 0 and 1")
    ordered = sorted(values)
    position = Decimal(len(ordered) - 1) * percentile
    lower_index = floor(position)
    upper_index = ceil(position)
    if lower_index == upper_index:
        return quantize(ordered[lower_index])
    fraction = position - Decimal(lower_index)
    interpolated = ordered[lower_index] + (ordered[upper_index] - ordered[lower_index]) * fraction
    return quantize(interpolated)


def price_variance_percent(actual_price: Decimal, benchmark_price: Decimal) -> Decimal:
    if benchmark_price <= 0:
        return ZERO.quantize(FOUR_PLACES)
    return quantize(((actual_price - benchmark_price) / benchmark_price) * HUNDRED)


def potential_savings(
    actual_price: Decimal, benchmark_price: Decimal, quantity: Decimal
) -> Decimal:
    if quantity < 0:
        raise ValueError("quantity cannot be negative")
    return quantize(max(ZERO, actual_price - benchmark_price) * quantity)


def confidence_score(
    *,
    supplier_count: int,
    transaction_count: int,
    quantity: Decimal,
    median_price: Decimal,
    p25_price: Decimal,
    p75_price: Decimal,
) -> Decimal:
    supplier_factor = min(Decimal(supplier_count) / Decimal(5), ONE)
    transaction_factor = min(Decimal(transaction_count) / Decimal(20), ONE)
    quantity_factor = min(Decimal(str(log10(float(quantity) + 1))) / Decimal(4), ONE)
    dispersion = abs(p75_price - p25_price) / median_price if median_price > 0 else ONE
    stability_factor = max(ZERO, ONE - min(dispersion, ONE))
    score = (
        supplier_factor * Decimal("0.35")
        + transaction_factor * Decimal("0.25")
        + quantity_factor * Decimal("0.20")
        + stability_factor * Decimal("0.20")
    )
    return quantize(min(max(score, ZERO), ONE))


def supplier_performance_score(
    *,
    price_score: Decimal,
    rejection_rate: Decimal,
    late_delivery_rate: Decimal,
    contract_compliance_rate: Decimal,
    config: OptimizationConfig,
) -> tuple[Decimal, dict[str, Decimal]]:
    quality_score = max(ZERO, HUNDRED * (ONE - rejection_rate))
    delivery_score = max(ZERO, HUNDRED * (ONE - late_delivery_rate))
    contract_score = max(ZERO, min(HUNDRED, HUNDRED * contract_compliance_rate))
    normalized_price_score = max(ZERO, min(HUNDRED, price_score))
    total = (
        normalized_price_score * config.supplier_score_price_weight
        + quality_score * config.supplier_score_quality_weight
        + delivery_score * config.supplier_score_delivery_weight
        + contract_score * config.supplier_score_contract_weight
    )
    components = {
        "price_score": quantize(normalized_price_score),
        "quality_score": quantize(quality_score),
        "delivery_score": quantize(delivery_score),
        "contract_score": quantize(contract_score),
    }
    return quantize(total), components


def priority_score(
    *,
    financial_impact: Decimal,
    confidence: Decimal,
    severity: Decimal,
    config: OptimizationConfig,
) -> tuple[Decimal, str]:
    impact_factor = min(financial_impact / config.priority_high_impact_amount, ONE)
    severity_factor = min(max(severity, ZERO), ONE)
    confidence_factor = min(max(confidence, ZERO), ONE)
    score = HUNDRED * (
        impact_factor * config.priority_impact_weight
        + confidence_factor * config.priority_confidence_weight
        + severity_factor * config.priority_severity_weight
    )
    value = quantize(score)
    if value >= 80:
        level = "CRITICAL"
    elif value >= 60:
        level = "HIGH"
    elif value >= 40:
        level = "MEDIUM"
    else:
        level = "LOW"
    return value, level
