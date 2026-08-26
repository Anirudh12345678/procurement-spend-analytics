import csv
import json
import logging
from collections.abc import Iterable, Sequence
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import BusinessUnit, Category, Item, PurchaseOrder, Supplier
from app.schemas.imports import (
    CsvPurchaseOrderRow,
    ImportSummary,
    RejectedRow,
    ValidationReport,
)

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = (
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
)


class CsvHeaderError(ValueError):
    """Raised when the source file cannot be safely interpreted."""


class InvalidRowsError(ValueError):
    """Raised in strict mode when validation finds rejected source rows."""


def _format_validation_error(error: ValidationError) -> list[str]:
    messages: list[str] = []
    for detail in error.errors(include_url=False):
        location = ".".join(str(part) for part in detail["loc"])
        messages.append(f"{location}: {detail['msg']}")
    return messages


def validate_csv(csv_path: Path) -> ValidationReport:
    """Validate all source rows without mutating the database."""

    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV source file not found: {csv_path}")

    valid_rows: list[CsvPurchaseOrderRow] = []
    rejected_rows: list[RejectedRow] = []
    seen_po_ids: set[str] = set()
    supplier_identity: dict[str, tuple[str, str]] = {}
    source_rows = 0

    with csv_path.open("r", newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        headers = reader.fieldnames or []
        missing_columns = [column for column in REQUIRED_COLUMNS if column not in headers]
        if missing_columns:
            raise CsvHeaderError("CSV is missing required columns: " + ", ".join(missing_columns))
        extra_columns = [column for column in headers if column not in REQUIRED_COLUMNS]
        if extra_columns:
            logger.warning("CSV contains unused extra columns: %s", ", ".join(extra_columns))

        for row_number, raw_row in enumerate(reader, start=2):
            source_rows += 1
            cleaned_raw = {key: value for key, value in raw_row.items() if key is not None}
            po_id = (cleaned_raw.get("po_id") or "").strip() or None
            errors: list[str] = []
            parsed: CsvPurchaseOrderRow | None = None

            try:
                parsed = CsvPurchaseOrderRow.model_validate(cleaned_raw)
            except ValidationError as exc:
                errors.extend(_format_validation_error(exc))

            if parsed is not None:
                if parsed.po_id in seen_po_ids:
                    errors.append("po_id: duplicate identifier within source CSV")

                known_supplier = supplier_identity.get(parsed.supplier_id)
                current_supplier = (parsed.supplier_name, parsed.supplier_country)
                if known_supplier is not None and known_supplier != current_supplier:
                    errors.append(
                        "supplier_id: maps to inconsistent supplier name or country "
                        f"(expected {known_supplier}, found {current_supplier})"
                    )

            if errors:
                rejected = RejectedRow(
                    row_number=row_number,
                    po_id=po_id,
                    errors=errors,
                    raw_data=cleaned_raw,
                )
                rejected_rows.append(rejected)
                logger.warning(
                    "Rejected CSV row %s (PO %s): %s",
                    row_number,
                    po_id or "unknown",
                    "; ".join(errors),
                )
                continue

            assert parsed is not None
            seen_po_ids.add(parsed.po_id)
            supplier_identity.setdefault(
                parsed.supplier_id, (parsed.supplier_name, parsed.supplier_country)
            )
            valid_rows.append(parsed)

    logger.info(
        "CSV validation complete: %s source rows, %s valid, %s rejected",
        source_rows,
        len(valid_rows),
        len(rejected_rows),
    )
    return ValidationReport(
        source_rows=source_rows,
        valid_rows=valid_rows,
        rejected_rows=rejected_rows,
        extra_columns=extra_columns,
    )


def write_rejection_report(report: ValidationReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_rows": report.source_rows,
        "valid_rows": report.valid_count,
        "rejected_rows": report.rejected_count,
        "rejections": [row.model_dump(mode="json") for row in report.rejected_rows],
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("Wrote validation rejection report to %s", output_path)


def _chunks(values: Sequence[str], chunk_size: int = 5_000) -> Iterable[Sequence[str]]:
    for start in range(0, len(values), chunk_size):
        yield values[start : start + chunk_size]


def _normalize_dimensions(
    session: Session, rows: Sequence[CsvPurchaseOrderRow]
) -> tuple[
    dict[str, Supplier],
    dict[str, Category],
    dict[tuple[str, str], Item],
    dict[str, BusinessUnit],
]:
    suppliers = {supplier.supplier_id: supplier for supplier in session.scalars(select(Supplier))}
    for row in rows:
        supplier = suppliers.get(row.supplier_id)
        if supplier is None:
            supplier = Supplier(
                supplier_id=row.supplier_id,
                supplier_name=row.supplier_name,
                supplier_country=row.supplier_country,
            )
            session.add(supplier)
            suppliers[row.supplier_id] = supplier
        else:
            supplier.supplier_name = row.supplier_name
            supplier.supplier_country = row.supplier_country

    categories = {
        category.category_name: category for category in session.scalars(select(Category))
    }
    for name in sorted({row.category for row in rows}):
        if name not in categories:
            category = Category(category_name=name)
            session.add(category)
            categories[name] = category

    business_units = {
        unit.business_unit_name: unit for unit in session.scalars(select(BusinessUnit))
    }
    for name in sorted({row.business_unit for row in rows}):
        if name not in business_units:
            unit = BusinessUnit(business_unit_name=name)
            session.add(unit)
            business_units[name] = unit

    session.flush()

    items = {
        (item.item_name, item.category.category_name): item
        for item in session.scalars(select(Item)).unique()
    }
    for item_name, category_name in sorted({(row.item, row.category) for row in rows}):
        key = (item_name, category_name)
        if key not in items:
            item = Item(item_name=item_name, category_id=categories[category_name].category_id)
            session.add(item)
            items[key] = item

    session.flush()
    return suppliers, categories, items, business_units


def _existing_po_ids(session: Session, po_ids: Sequence[str]) -> set[str]:
    existing: set[str] = set()
    for chunk in _chunks(po_ids):
        existing.update(
            session.scalars(select(PurchaseOrder.po_id).where(PurchaseOrder.po_id.in_(chunk)))
        )
    return existing


def _purchase_order_mapping(
    row: CsvPurchaseOrderRow,
    items: dict[tuple[str, str], Item],
    business_units: dict[str, BusinessUnit],
) -> dict[str, object]:
    return {
        "po_id": row.po_id,
        "order_date": row.order_date,
        "promised_delivery_date": row.promised_delivery_date,
        "actual_delivery_date": row.actual_delivery_date,
        "supplier_id": row.supplier_id,
        "item_id": items[(row.item, row.category)].item_id,
        "business_unit_id": business_units[row.business_unit].business_unit_id,
        "quantity": row.quantity,
        "unit_price": row.unit_price,
        "line_total": row.line_total,
        "payment_terms": row.payment_terms,
        "on_contract": row.on_contract,
        "quality_rejected": row.quality_rejected,
    }


def import_purchase_orders(
    session: Session,
    csv_path: Path,
    *,
    allow_partial: bool = False,
    rejection_report_path: Path | None = None,
    batch_size: int = 1_000,
) -> ImportSummary:
    """Validate and import CSV data in the caller's database transaction."""

    validation = validate_csv(csv_path)
    if rejection_report_path is not None:
        write_rejection_report(validation, rejection_report_path)
    if validation.rejected_rows and not allow_partial:
        raise InvalidRowsError(
            f"Validation rejected {validation.rejected_count} rows; no data was imported. "
            "Inspect the rejection report or explicitly enable partial imports."
        )

    _, _, items, business_units = _normalize_dimensions(session, validation.valid_rows)
    po_ids = [row.po_id for row in validation.valid_rows]
    existing_ids = _existing_po_ids(session, po_ids)
    mappings = [
        _purchase_order_mapping(row, items, business_units) for row in validation.valid_rows
    ]
    inserts = [mapping for mapping in mappings if mapping["po_id"] not in existing_ids]
    updates = [mapping for mapping in mappings if mapping["po_id"] in existing_ids]

    for start in range(0, len(inserts), batch_size):
        session.bulk_insert_mappings(PurchaseOrder, inserts[start : start + batch_size])
    for start in range(0, len(updates), batch_size):
        session.bulk_update_mappings(PurchaseOrder, updates[start : start + batch_size])
    session.flush()

    total_spend = session.scalar(select(func.coalesce(func.sum(PurchaseOrder.line_total), 0)))
    summary = ImportSummary(
        source_file=str(csv_path.resolve()),
        source_rows=validation.source_rows,
        valid_rows=validation.valid_count,
        rejected_rows=validation.rejected_count,
        inserted_purchase_orders=len(inserts),
        updated_purchase_orders=len(updates),
        supplier_count=session.scalar(select(func.count()).select_from(Supplier)) or 0,
        category_count=session.scalar(select(func.count()).select_from(Category)) or 0,
        item_count=session.scalar(select(func.count()).select_from(Item)) or 0,
        business_unit_count=session.scalar(select(func.count()).select_from(BusinessUnit)) or 0,
        purchase_order_count=session.scalar(select(func.count()).select_from(PurchaseOrder)) or 0,
        total_spend=Decimal(total_spend),
        rejection_report=str(rejection_report_path.resolve()) if rejection_report_path else None,
    )
    logger.info(
        "Import complete: %s inserted, %s updated, %s total purchase orders",
        summary.inserted_purchase_orders,
        summary.updated_purchase_orders,
        summary.purchase_order_count,
    )
    return summary
