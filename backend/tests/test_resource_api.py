from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.main import app
from app.optimization.engine import OptimizationEngine
from tests.test_optimization import optimization_config


@contextmanager
def client_for(session: Session) -> Iterator[TestClient]:
    def override_db() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def test_reference_endpoints_and_pagination(analytics_session: Session) -> None:
    with client_for(analytics_session) as client:
        suppliers = client.get("/api/suppliers", params={"page": 1, "page_size": 2})
        categories = client.get("/api/categories")
        items = client.get("/api/items", params={"page_size": 1})
        units = client.get("/api/business-units")

        assert suppliers.status_code == 200
        assert suppliers.json()["total"] == 3
        assert suppliers.json()["page_size"] == 2
        assert len(suppliers.json()["items"]) == 2
        assert categories.status_code == 200
        assert len(categories.json()) == 2
        assert items.status_code == 200
        assert items.json()["total"] == 2
        assert len(items.json()["items"]) == 1
        assert units.status_code == 200
        assert len(units.json()) == 2


def test_reference_detail_and_consistent_not_found_error(
    analytics_session: Session,
) -> None:
    with client_for(analytics_session) as client:
        found = client.get("/api/suppliers/SUP-001")
        missing = client.get("/api/suppliers/UNKNOWN")

        assert found.status_code == 200
        assert found.json()["transaction_count"] == 2
        assert missing.status_code == 404
        assert missing.json() == {
            "error": {
                "code": "SUPPLIER_NOT_FOUND",
                "message": "Supplier was not found",
            }
        }


def test_benchmark_and_opportunity_endpoints_use_stored_results(
    analytics_session: Session,
) -> None:
    _, opportunities = OptimizationEngine(analytics_session, optimization_config()).run()
    analytics_session.flush()
    with client_for(analytics_session) as client:
        benchmarks = client.get("/api/benchmarks", params={"page_size": 1})
        benchmark_id = benchmarks.json()["items"][0]["item_id"]
        benchmark = client.get(f"/api/benchmarks/{benchmark_id}")
        opportunity_page = client.get("/api/opportunities", params={"page_size": 2})
        opportunity = client.get(f"/api/opportunities/{opportunities[0].opportunity_id}")
        summary = client.get("/api/opportunities/summary")

        assert benchmarks.status_code == 200
        assert benchmarks.json()["total"] == 2
        assert benchmark.status_code == 200
        assert opportunity_page.status_code == 200
        assert opportunity_page.json()["total"] == len(opportunities)
        assert len(opportunity_page.json()["items"]) == min(2, len(opportunities))
        assert opportunity.status_code == 200
        assert "supporting_metrics" in opportunity.json()
        assert summary.status_code == 200
        assert summary.json()["active_opportunity_count"] == len(opportunities)
        assert "not additive" in summary.json()["savings_note"]


def test_opportunity_filter_validation_and_error_shape(analytics_session: Session) -> None:
    OptimizationEngine(analytics_session, optimization_config()).run()
    with client_for(analytics_session) as client:
        filtered = client.get("/api/opportunities", params={"opportunity_type": "CONTRACT_LEAKAGE"})
        invalid_page = client.get("/api/opportunities", params={"page_size": 101})
        invalid_type = client.get("/api/opportunities", params={"opportunity_type": "NOT_REAL"})

        assert filtered.status_code == 200
        assert all(
            item["opportunity_type"] == "CONTRACT_LEAKAGE" for item in filtered.json()["items"]
        )
        assert invalid_page.status_code == 422
        assert invalid_page.json()["error"]["code"] == "VALIDATION_ERROR"
        assert invalid_type.status_code == 422
        assert invalid_type.json()["error"]["code"] == "VALIDATION_ERROR"


def test_openapi_and_configured_cors(analytics_session: Session) -> None:
    with client_for(analytics_session) as client:
        openapi = client.get("/openapi.json")
        preflight = client.options(
            "/api/dashboard/summary",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert openapi.status_code == 200
        assert "/api/opportunities" in openapi.json()["paths"]
        assert preflight.status_code == 200
        assert preflight.headers["access-control-allow-origin"] == "http://localhost:5173"
