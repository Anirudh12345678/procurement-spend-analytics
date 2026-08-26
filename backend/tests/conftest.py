import csv
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models import Base
from app.services.importer import import_purchase_orders

HEADERS = [
    "po_id",
    "order_date",
    "promised_delivery_date",
    "actual_delivery_date",
    "supplier_id",
    "supplier_name",
    "supplier_country",
    "category",
    "item",
    "business_unit",
    "unit_price",
    "quantity",
    "line_total",
    "payment_terms",
    "on_contract",
    "quality_rejected",
]


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    with Session(engine) as test_session:
        with test_session.begin():
            yield test_session


@pytest.fixture
def valid_row() -> dict[str, str]:
    return {
        "po_id": "PO-TEST-001",
        "order_date": "2026-01-01",
        "promised_delivery_date": "2026-01-10",
        "actual_delivery_date": "2026-01-12",
        "supplier_id": "SUP-001",
        "supplier_name": "Test Supplier",
        "supplier_country": "India",
        "category": "IT",
        "item": "Laptop",
        "business_unit": "Operations",
        "unit_price": "100.25",
        "quantity": "2",
        "line_total": "200.50",
        "payment_terms": "Net 30",
        "on_contract": "True",
        "quality_rejected": "False",
    }


@pytest.fixture
def write_csv(tmp_path: Path):
    def _write(rows: list[dict[str, str]], headers: list[str] | None = None) -> Path:
        path = tmp_path / "purchase_orders.csv"
        fieldnames = headers or HEADERS
        with path.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return path

    return _write


@pytest.fixture
def analytics_session(session: Session, valid_row: dict[str, str], write_csv) -> Session:
    rows: list[dict[str, str]] = []

    first = valid_row.copy()
    first.update(
        {
            "po_id": "PO-TEST-001",
            "order_date": "2026-01-01",
            "promised_delivery_date": "2026-01-10",
            "actual_delivery_date": "2026-01-12",
            "unit_price": "100.00",
            "quantity": "2",
            "line_total": "200.00",
        }
    )
    rows.append(first)

    second = first.copy()
    second.update(
        {
            "po_id": "PO-TEST-002",
            "order_date": "2026-01-15",
            "promised_delivery_date": "2026-01-20",
            "actual_delivery_date": "2026-01-20",
            "quantity": "1",
            "line_total": "100.00",
            "on_contract": "False",
            "quality_rejected": "True",
        }
    )
    rows.append(second)

    third = first.copy()
    third.update(
        {
            "po_id": "PO-TEST-003",
            "order_date": "2026-01-20",
            "promised_delivery_date": "2026-01-25",
            "actual_delivery_date": "2026-01-25",
            "supplier_id": "SUP-002",
            "supplier_name": "US Supplier",
            "supplier_country": "United States",
            "item": "Laptop",
            "unit_price": "50.00",
            "quantity": "2",
            "line_total": "100.00",
        }
    )
    rows.append(third)

    fourth = third.copy()
    fourth.update(
        {
            "po_id": "PO-TEST-004",
            "order_date": "2026-02-01",
            "promised_delivery_date": "2026-02-05",
            "actual_delivery_date": "2026-02-08",
            "unit_price": "100.00",
            "quantity": "2",
            "line_total": "200.00",
        }
    )
    rows.append(fourth)

    fifth = first.copy()
    fifth.update(
        {
            "po_id": "PO-TEST-005",
            "order_date": "2026-02-10",
            "promised_delivery_date": "2026-02-15",
            "actual_delivery_date": "2026-02-20",
            "supplier_id": "SUP-003",
            "supplier_name": "Office Supplier",
            "category": "Office",
            "item": "Desk",
            "business_unit": "Finance",
            "unit_price": "200.00",
            "quantity": "2",
            "line_total": "400.00",
            "on_contract": "False",
            "quality_rejected": "True",
        }
    )
    rows.append(fifth)

    import_purchase_orders(session, write_csv(rows))
    return session
