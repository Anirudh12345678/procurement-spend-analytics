from collections.abc import Iterator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_recommendation_client
from app.config import Settings
from app.main import app
from app.models import AIRecommendation
from app.optimization.engine import OptimizationEngine
from app.schemas.recommendations import GeneratedRecommendation
from app.services.llm import OpenAIResponsesClient
from app.services.recommendations import RecommendationService
from tests.test_optimization import optimization_config


class MockLLM:
    model_name = "mock-model"

    def __init__(self, response: dict):
        self.response = response
        self.calls = 0

    def generate(self, *, system_prompt: str, context_json: str, schema: dict) -> dict:
        self.calls += 1
        assert "Do not invent" in system_prompt
        assert "estimated_savings" in context_json
        assert schema["title"] == "GeneratedRecommendation"
        return self.response


class TransactionSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def valid_output(impact: Decimal) -> dict:
    return {
        "title": "Review verified procurement finding",
        "summary": "The verified analytical context supports a focused procurement review.",
        "reasoning": "The recommendation relies only on the supplied deterministic evidence.",
        "recommended_action": (
            "Evaluate negotiation and qualified alternatives while protecting service quality."
        ),
        "estimated_impact": str(impact),
        "risks": "Commercial feasibility and service continuity require validation.",
        "next_steps": ["Confirm the purchase-order scope with procurement owners."],
    }


@pytest.fixture
def opportunity_id(analytics_session: Session) -> int:
    _, opportunities = OptimizationEngine(analytics_session, optimization_config()).run()
    return opportunities[0].opportunity_id


def test_pydantic_output_rejects_unsafe_or_malformed_content() -> None:
    with pytest.raises(ValidationError):
        GeneratedRecommendation.model_validate({"title": "Too short"})
    payload = valid_output(Decimal("100"))
    payload["summary"] = "This provides guaranteed savings for the procurement team."
    with pytest.raises(ValidationError, match="guaranteed"):
        GeneratedRecommendation.model_validate(payload)


def test_openai_schema_is_converted_to_strict_supported_shape() -> None:
    schema = OpenAIResponsesClient._strict_schema(GeneratedRecommendation.model_json_schema())
    assert isinstance(schema, dict)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    assert "default" not in str(schema)
    assert "minLength" not in str(schema)


def test_database_dependency_commits_successful_write_requests(monkeypatch) -> None:
    session = TransactionSession()
    monkeypatch.setattr("app.api.dependencies.SessionLocal", lambda: session)
    dependency = get_db()

    assert next(dependency) is session
    with pytest.raises(StopIteration):
        next(dependency)

    assert session.committed is True
    assert session.rolled_back is False
    assert session.closed is True


def test_database_dependency_rolls_back_failed_requests(monkeypatch) -> None:
    session = TransactionSession()
    monkeypatch.setattr("app.api.dependencies.SessionLocal", lambda: session)
    dependency = get_db()
    next(dependency)

    with pytest.raises(RuntimeError, match="request failed"):
        dependency.throw(RuntimeError("request failed"))

    assert session.committed is False
    assert session.rolled_back is True
    assert session.closed is True


def test_valid_mocked_recommendation_preserves_impact_and_is_stored(
    analytics_session: Session, opportunity_id: int
) -> None:
    service = RecommendationService(analytics_session)
    context = service._context(opportunity_id)
    assert context is not None
    mock = MockLLM(valid_output(context.expected_impact))

    result = service.generate(opportunity_id, client=mock)

    assert result is not None
    assert result.model_name == "mock-model"
    assert Decimal(result.estimated_impact) == context.expected_impact
    assert result.context_snapshot["estimated_savings"] == str(context.estimated_savings)
    assert mock.calls == 1
    assert analytics_session.scalar(select(func.count()).select_from(AIRecommendation)) == 1


def test_malformed_model_output_retries_then_uses_safe_fallback(
    analytics_session: Session, opportunity_id: int
) -> None:
    mock = MockLLM({"title": "invalid"})

    result = RecommendationService(analytics_session).generate(opportunity_id, client=mock)

    assert result is not None
    assert result.model_name == "deterministic-fallback"
    assert "fallback" in result.reasoning.lower()
    assert mock.calls == 2


def test_modified_numeric_impact_is_rejected_and_falls_back(
    analytics_session: Session, opportunity_id: int
) -> None:
    service = RecommendationService(analytics_session)
    context = service._context(opportunity_id)
    assert context is not None
    mock = MockLLM(valid_output(context.expected_impact + Decimal("1")))

    result = service.generate(opportunity_id, client=mock)

    assert result is not None
    assert result.model_name == "deterministic-fallback"
    assert Decimal(result.estimated_impact) == context.expected_impact
    assert mock.calls == 2


def test_invented_number_in_text_is_rejected(
    analytics_session: Session, opportunity_id: int
) -> None:
    service = RecommendationService(analytics_session)
    context = service._context(opportunity_id)
    assert context is not None
    payload = valid_output(context.expected_impact)
    payload["reasoning"] = "The unsupported market comparison indicates a value of 999999."
    mock = MockLLM(payload)

    result = service.generate(opportunity_id, client=mock)

    assert result is not None
    assert result.model_name == "deterministic-fallback"


def test_missing_api_key_uses_fallback_without_provider_call(
    analytics_session: Session, opportunity_id: int
) -> None:
    settings = Settings.model_construct(
        database_url="sqlite://", openai_api_key=None, openai_model="unused"
    )

    result = RecommendationService(analytics_session, settings=settings).generate(opportunity_id)

    assert result is not None
    assert result.model_name == "deterministic-fallback"
    assert "no server-side API key" in result.reasoning


def test_recommendation_api_uses_mock_and_supports_listing(
    analytics_session: Session, opportunity_id: int
) -> None:
    service = RecommendationService(analytics_session)
    context = service._context(opportunity_id)
    assert context is not None
    mock = MockLLM(valid_output(context.expected_impact))

    def override_db() -> Iterator[Session]:
        yield analytics_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_recommendation_client] = lambda: mock
    try:
        with TestClient(app) as client:
            generated = client.post(
                "/api/recommendations/generate",
                json={"opportunity_id": opportunity_id},
            )
            listed = client.get("/api/recommendations")
            detail = client.get(f"/api/recommendations/{generated.json()['recommendation_id']}")

        assert generated.status_code == 201
        assert generated.json()["estimated_impact"] == str(context.expected_impact)
        assert listed.status_code == 200
        assert listed.json()["total"] == 1
        assert detail.status_code == 200
        assert detail.json()["model_name"] == "mock-model"
    finally:
        app.dependency_overrides.clear()
