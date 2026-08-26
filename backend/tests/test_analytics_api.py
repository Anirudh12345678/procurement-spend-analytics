from collections.abc import Iterator
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.main import app


def test_analytics_routes_return_typed_results(analytics_session: Session) -> None:
    def override_db() -> Iterator[Session]:
        yield analytics_session

    app.dependency_overrides[get_db] = override_db
    routes = [
        "/api/dashboard/summary",
        "/api/analytics/spend/suppliers",
        "/api/analytics/supplier-concentration",
        "/api/analytics/spend/categories",
        "/api/analytics/spend/business-units",
        "/api/analytics/spend/monthly",
        "/api/analytics/contract-compliance",
        "/api/analytics/quality",
        "/api/analytics/delivery",
    ]
    try:
        with TestClient(app) as client:
            for route in routes:
                response = client.get(route)
                assert response.status_code == 200, (route, response.text)
    finally:
        app.dependency_overrides.clear()


def test_api_filters_and_invalid_date_ranges(analytics_session: Session) -> None:
    def override_db() -> Iterator[Session]:
        yield analytics_session

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            filtered = client.get(
                "/api/dashboard/summary",
                params={"date_from": "2026-02-01", "date_to": "2026-02-28"},
            )
            invalid = client.get(
                "/api/dashboard/summary",
                params={"date_from": "2026-03-01", "date_to": "2026-02-01"},
            )

        assert filtered.status_code == 200
        assert Decimal(str(filtered.json()["total_spend"])) == Decimal("600.0000")
        assert filtered.json()["total_orders"] == 2
        assert invalid.status_code == 422
        assert "date_from cannot be after date_to" in invalid.text
    finally:
        app.dependency_overrides.clear()
