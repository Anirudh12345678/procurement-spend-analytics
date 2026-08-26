import argparse
import logging
from pathlib import Path

from app.config import get_settings
from app.database import session_scope
from app.logging_config import configure_logging
from app.services.importer import InvalidRowsError, import_purchase_orders

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and import procurement purchase orders")
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("../purchase_orders.csv"),
        help="Path to purchase_orders.csv (default: ../purchase_orders.csv)",
    )
    parser.add_argument(
        "--rejection-report",
        type=Path,
        default=Path("../data/import_rejections.json"),
        help="JSON path for validation results and rejected rows",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Import valid rows even if other source rows fail validation",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)

    try:
        with session_scope() as session:
            summary = import_purchase_orders(
                session,
                args.csv,
                allow_partial=args.allow_partial,
                rejection_report_path=args.rejection_report,
            )
    except (FileNotFoundError, InvalidRowsError, ValueError) as exc:
        logger.error("Import failed: %s", exc)
        return 1

    print(summary.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
