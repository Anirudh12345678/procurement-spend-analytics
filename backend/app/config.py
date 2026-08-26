from functools import lru_cache

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or the root .env file."""

    database_url: str = Field(validation_alias="DATABASE_URL")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    app_currency: str = Field(default="USD", validation_alias="APP_CURRENCY")
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        validation_alias="CORS_ORIGINS",
    )
    openai_api_key: SecretStr | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5.4-mini", validation_alias="OPENAI_MODEL")
    openai_timeout_seconds: float = Field(
        default=30, gt=0, le=120, validation_alias="OPENAI_TIMEOUT_SECONDS"
    )

    price_variance_threshold_percent: float = Field(
        default=10, ge=0, validation_alias="PRICE_VARIANCE_THRESHOLD_PERCENT"
    )
    min_price_opportunity_savings: float = Field(
        default=5_000, ge=0, validation_alias="MIN_PRICE_OPPORTUNITY_SAVINGS"
    )
    min_benchmark_suppliers: int = Field(
        default=3, ge=2, validation_alias="MIN_BENCHMARK_SUPPLIERS"
    )
    contract_leakage_min_spend: float = Field(
        default=100_000, ge=0, validation_alias="CONTRACT_LEAKAGE_MIN_SPEND"
    )
    consolidation_min_spend: float = Field(
        default=250_000, ge=0, validation_alias="CONSOLIDATION_MIN_SPEND"
    )
    consolidation_min_suppliers: int = Field(
        default=3, ge=2, validation_alias="CONSOLIDATION_MIN_SUPPLIERS"
    )
    consolidation_min_dispersion_percent: float = Field(
        default=15, ge=0, validation_alias="CONSOLIDATION_MIN_DISPERSION_PERCENT"
    )
    supplier_performance_min_spend: float = Field(
        default=250_000, ge=0, validation_alias="SUPPLIER_PERFORMANCE_MIN_SPEND"
    )
    supplier_performance_score_threshold: float = Field(
        default=75, ge=0, le=100, validation_alias="SUPPLIER_PERFORMANCE_SCORE_THRESHOLD"
    )
    supplier_score_price_weight: float = Field(
        default=0.40, ge=0, le=1, validation_alias="SUPPLIER_SCORE_PRICE_WEIGHT"
    )
    supplier_score_quality_weight: float = Field(
        default=0.25, ge=0, le=1, validation_alias="SUPPLIER_SCORE_QUALITY_WEIGHT"
    )
    supplier_score_delivery_weight: float = Field(
        default=0.20, ge=0, le=1, validation_alias="SUPPLIER_SCORE_DELIVERY_WEIGHT"
    )
    supplier_score_contract_weight: float = Field(
        default=0.15, ge=0, le=1, validation_alias="SUPPLIER_SCORE_CONTRACT_WEIGHT"
    )
    priority_impact_weight: float = Field(
        default=0.50, ge=0, le=1, validation_alias="PRIORITY_IMPACT_WEIGHT"
    )
    priority_confidence_weight: float = Field(
        default=0.30, ge=0, le=1, validation_alias="PRIORITY_CONFIDENCE_WEIGHT"
    )
    priority_severity_weight: float = Field(
        default=0.20, ge=0, le=1, validation_alias="PRIORITY_SEVERITY_WEIGHT"
    )
    priority_high_impact_amount: float = Field(
        default=1_000_000, gt=0, validation_alias="PRIORITY_HIGH_IMPACT_AMOUNT"
    )

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_weight_totals(self) -> "Settings":
        supplier_total = (
            self.supplier_score_price_weight
            + self.supplier_score_quality_weight
            + self.supplier_score_delivery_weight
            + self.supplier_score_contract_weight
        )
        priority_total = (
            self.priority_impact_weight
            + self.priority_confidence_weight
            + self.priority_severity_weight
        )
        if abs(supplier_total - 1) > 0.0001:
            raise ValueError("supplier score weights must sum to 1")
        if abs(priority_total - 1) > 0.0001:
            raise ValueError("priority weights must sum to 1")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
