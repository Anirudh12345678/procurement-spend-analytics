from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.imports import CsvPurchaseOrderRow
from app.services.importer import CsvHeaderError, validate_csv


def test_valid_row_is_parsed_with_exact_decimal_values(valid_row: dict[str, str]) -> None:
    row = CsvPurchaseOrderRow.model_validate(valid_row)

    assert row.unit_price == Decimal("100.25")
    assert row.quantity == Decimal("2")
    assert row.line_total == Decimal("200.50")
    assert row.on_contract is True
    assert row.quality_rejected is False


def test_line_total_mismatch_is_rejected(valid_row: dict[str, str]) -> None:
    valid_row["line_total"] = "201.00"

    with pytest.raises(ValidationError, match="line_total does not match"):
        CsvPurchaseOrderRow.model_validate(valid_row)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("quantity", "0"),
        ("unit_price", "-1"),
        ("line_total", "-1"),
        ("on_contract", "yes"),
        ("actual_delivery_date", "2025-12-31"),
    ],
)
def test_invalid_source_values_are_rejected(
    valid_row: dict[str, str], field: str, value: str
) -> None:
    valid_row[field] = value

    with pytest.raises(ValidationError):
        CsvPurchaseOrderRow.model_validate(valid_row)


def test_duplicate_po_id_is_reported(valid_row: dict[str, str], write_csv) -> None:
    path = write_csv([valid_row, valid_row.copy()])

    report = validate_csv(path)

    assert report.source_rows == 2
    assert report.valid_count == 1
    assert report.rejected_count == 1
    assert "duplicate identifier" in report.rejected_rows[0].errors[0]


def test_missing_required_header_fails_the_file(valid_row: dict[str, str], write_csv) -> None:
    headers = [key for key in valid_row if key != "po_id"]
    row_without_po_id = {key: value for key, value in valid_row.items() if key != "po_id"}
    path = write_csv([row_without_po_id], headers=headers)

    with pytest.raises(CsvHeaderError, match="po_id"):
        validate_csv(path)


def test_supplier_identity_conflict_is_reported(valid_row: dict[str, str], write_csv) -> None:
    conflicting = valid_row.copy()
    conflicting["po_id"] = "PO-TEST-002"
    conflicting["supplier_name"] = "Different Supplier"
    path = write_csv([valid_row, conflicting])

    report = validate_csv(path)

    assert report.valid_count == 1
    assert report.rejected_count == 1
    assert "inconsistent supplier" in report.rejected_rows[0].errors[0]
