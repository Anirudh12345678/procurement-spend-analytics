from collections import Counter
from decimal import Decimal

from app.config import get_settings
from app.database import session_scope
from app.logging_config import configure_logging
from app.optimization.engine import OptimizationEngine


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    with session_scope() as session:
        benchmarks, opportunities = OptimizationEngine(session).run()
        counts = Counter(item.opportunity_type for item in opportunities)
        estimated_savings = sum(
            (
                Decimal(item.estimated_savings)
                for item in opportunities
                if item.opportunity_type == "PRICE_OPTIMIZATION"
            ),
            start=Decimal(0),
        )
        review_spend = {
            opportunity_type: str(
                sum(
                    (
                        Decimal(item.review_spend)
                        for item in opportunities
                        if item.opportunity_type == opportunity_type
                    ),
                    start=Decimal(0),
                )
            )
            for opportunity_type in counts
        }
    print(
        {
            "benchmarks": len(benchmarks),
            "active_opportunities": len(opportunities),
            "opportunities_by_type": dict(counts),
            "estimated_price_optimization_savings": str(estimated_savings),
            "review_spend_by_type": review_spend,
            "savings_note": (
                "Estimated opportunities are not guaranteed and types are not additive."
            ),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
