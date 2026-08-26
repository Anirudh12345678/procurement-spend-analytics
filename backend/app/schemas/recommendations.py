from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator


class RecommendationContext(BaseModel):
    opportunity_id: int
    opportunity_type: str
    item: str
    supplier: str | None
    actual_price: Decimal | None
    benchmark_price: Decimal | None
    price_variance_percent: Decimal | None
    quantity: Decimal | None
    estimated_savings: Decimal
    review_spend: Decimal
    confidence_score: Decimal
    supplier_score: Decimal | None = None
    quality_rejection_rate: Decimal | None = None
    late_delivery_rate: Decimal | None = None
    contract_compliance_rate: Decimal | None = None
    supporting_metrics: dict[str, object] = Field(default_factory=dict)

    @property
    def expected_impact(self) -> Decimal:
        if self.estimated_savings > 0:
            return self.estimated_savings
        return self.review_spend


class GeneratedRecommendation(BaseModel):
    title: str = Field(min_length=5, max_length=255)
    summary: str = Field(min_length=20)
    reasoning: str = Field(min_length=20)
    recommended_action: str = Field(min_length=10)
    estimated_impact: Decimal = Field(ge=0)
    risks: str | None = None
    next_steps: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("next_steps")
    @classmethod
    def validate_next_steps(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("next_steps cannot contain empty values")
        return values

    @model_validator(mode="after")
    def reject_guaranteed_savings_language(self) -> "GeneratedRecommendation":
        combined = " ".join(
            filter(
                None,
                [
                    self.title,
                    self.summary,
                    self.reasoning,
                    self.recommended_action,
                    self.risks,
                    *self.next_steps,
                ],
            )
        ).lower()
        qualified = combined.replace("not guaranteed savings", "").replace(
            "without assuming guaranteed savings", ""
        )
        if "guaranteed savings" in qualified or "guarantee savings" in qualified:
            raise ValueError("recommendation cannot claim guaranteed savings")
        return self


class GenerateRecommendationRequest(BaseModel):
    opportunity_id: int = Field(ge=1)
    force: bool = False


class RecommendationResponse(BaseModel):
    recommendation_id: int
    opportunity_id: int
    opportunity_type: str
    item_name: str
    supplier_name: str | None
    title: str
    summary: str
    reasoning: str
    recommended_action: str
    estimated_impact: Decimal
    risks: str | None
    next_steps: list[str]
    confidence_score: Decimal
    model_name: str
    prompt_version: str
    created_at: datetime
