from collections.abc import Generator
from datetime import date
from typing import Annotated

from fastapi import Depends, Query
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.schemas.analytics import AnalyticsFilters
from app.schemas.api import PaginationParams
from app.services.llm import RecommendationLLM


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_analytics_filters(
    date_from: Annotated[date | None, Query(description="Inclusive order-date start")] = None,
    date_to: Annotated[date | None, Query(description="Inclusive order-date end")] = None,
    supplier_id: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
    category_id: Annotated[int | None, Query(ge=1)] = None,
    business_unit_id: Annotated[int | None, Query(ge=1)] = None,
    country: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
) -> AnalyticsFilters:
    try:
        return AnalyticsFilters(
            date_from=date_from,
            date_to=date_to,
            supplier_id=supplier_id,
            category_id=category_id,
            business_unit_id=business_unit_id,
            country=country,
        )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc


DatabaseSession = Annotated[Session, Depends(get_db)]
CommonAnalyticsFilters = Annotated[AnalyticsFilters, Depends(get_analytics_filters)]


def get_pagination(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)


Pagination = Annotated[PaginationParams, Depends(get_pagination)]


def get_recommendation_client() -> RecommendationLLM | None:
    """Production uses the configured OpenAI client; tests may override this dependency."""

    return None


RecommendationClient = Annotated[RecommendationLLM | None, Depends(get_recommendation_client)]
