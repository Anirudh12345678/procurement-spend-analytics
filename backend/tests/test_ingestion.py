import json
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import BusinessUnit, Category, Item, PurchaseOrder, Supplier
from app.services.importer import InvalidRowsError, import_purchase_orders
from app.services.verification import verify_database


def test_import_normalizes_dimensions_and_preserves_relationships(
    session: Session, valid_row: dict[str, str], write_csv
) -> None:
    second = valid_row.copy()
    second.update(
        {
            "po_id": "PO-TEST-002",
            "item": "Monitor",
            "unit_price": "50.00",
            "quantity": "3",
            "line_total": "150.00",
        }
    )
    csv_path = write_csv([valid_row, second])

    summary = import_purchase_orders(session, csv_path)

    assert summary.inserted_purchase_orders == 2
    assert summary.updated_purchase_orders == 0
    assert summary.supplier_count == 1
    assert summary.category_count == 1
    assert summary.item_count == 2
    assert summary.business_unit_count == 1
    assert summary.total_spend == Decimal("350.5000")

    purchase_order = session.get(PurchaseOrder, "PO-TEST-001")
    assert purchase_order is not None
    assert purchase_order.supplier.supplier_name == "Test Supplier"
    assert purchase_order.item.category.category_name == "IT"
    assert purchase_order.business_unit.business_unit_name == "Operations"


def test_import_is_idempotent_and_updates_changed_source_values(
    session: Session, valid_row: dict[str, str], write_csv
) -> None:
    csv_path = write_csv([valid_row])
    first = import_purchase_orders(session, csv_path)

    valid_row["payment_terms"] = "Net 45"
    csv_path = write_csv([valid_row])
    second = import_purchase_orders(session, csv_path)

    assert first.inserted_purchase_orders == 1
    assert second.inserted_purchase_orders == 0
    assert second.updated_purchase_orders == 1
    assert session.scalar(select(func.count()).select_from(PurchaseOrder)) == 1
    assert session.get(PurchaseOrder, "PO-TEST-001").payment_terms == "Net 45"


def test_strict_import_writes_rejections_and_inserts_nothing(
    session: Session, valid_row: dict[str, str], write_csv, tmp_path
) -> None:
    invalid = valid_row.copy()
    invalid["line_total"] = "999.99"
    csv_path = write_csv([invalid])
    rejection_path = tmp_path / "rejections.json"

    with pytest.raises(InvalidRowsError):
        import_purchase_orders(session, csv_path, rejection_report_path=rejection_path)

    assert session.scalar(select(func.count()).select_from(PurchaseOrder)) == 0
    payload = json.loads(rejection_path.read_text(encoding="utf-8"))
    assert payload["rejected_rows"] == 1
    assert payload["rejections"][0]["po_id"] == "PO-TEST-001"


def test_database_verification_detects_no_duplicates_or_orphans(
    session: Session, valid_row: dict[str, str], write_csv
) -> None:
    import_purchase_orders(session, write_csv([valid_row]))

    result = verify_database(session)

    assert result.is_valid
    assert result.purchase_order_count == 1
    assert result.duplicate_po_ids == 0
    assert result.orphan_supplier_relationships == 0
    assert result.orphan_item_relationships == 0
    assert result.orphan_business_unit_relationships == 0
    assert result.total_spend == Decimal("200.5000")


def test_expected_dimension_tables_exist(session: Session) -> None:
    assert session.scalar(select(func.count()).select_from(Supplier)) == 0
    assert session.scalar(select(func.count()).select_from(Category)) == 0
    assert session.scalar(select(func.count()).select_from(Item)) == 0
    assert session.scalar(select(func.count()).select_from(BusinessUnit)) == 0
