import logging

from app.config import get_settings
from app.database import session_scope
from app.logging_config import configure_logging
from app.services.verification import verify_database


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    with session_scope() as session:
        result = verify_database(session)
    print(result.model_dump_json(indent=2))
    if not result.is_valid:
        logging.getLogger(__name__).error("Database verification failed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
