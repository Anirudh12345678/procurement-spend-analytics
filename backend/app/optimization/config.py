from decimal import Decimal

from pydantic import BaseModel, Field

from app.config import Settings


class OptimizationConfig(BaseModel):
    price_variance_threshold_percent: Decimal = Field(ge=0)
    min_price_opportunity_savings: Decimal = Field(ge=0)
    min_benchmark_suppliers: int = Field(ge=2)
    contract_leakage_min_spend: Decimal = Field(ge=0)
    consolidation_min_spend: Decimal = Field(ge=0)
    consolidation_min_suppliers: int = Field(ge=2)
    consolidation_min_dispersion_percent: Decimal = Field(ge=0)
    supplier_performance_min_spend: Decimal = Field(ge=0)
    supplier_performance_score_threshold: Decimal = Field(ge=0, le=100)
    supplier_score_price_weight: Decimal = Field(ge=0, le=1)
    supplier_score_quality_weight: Decimal = Field(ge=0, le=1)
    supplier_score_delivery_weight: Decimal = Field(ge=0, le=1)
    supplier_score_contract_weight: Decimal = Field(ge=0, le=1)
    priority_impact_weight: Decimal = Field(ge=0, le=1)
    priority_confidence_weight: Decimal = Field(ge=0, le=1)
    priority_severity_weight: Decimal = Field(ge=0, le=1)
    priority_high_impact_amount: Decimal = Field(gt=0)

    @classmethod
    def from_settings(cls, settings: Settings) -> "OptimizationConfig":
        return cls(
            **{
                field: Decimal(str(getattr(settings, field)))
                if field not in {"min_benchmark_suppliers", "consolidation_min_suppliers"}
                else getattr(settings, field)
                for field in cls.model_fields
            }
        )
