from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import DatabaseSession, Pagination
from app.schemas.api import ErrorResponse, PaginatedResponse
from app.schemas.optimization import (
    BenchmarkResponse,
    OpportunityResponse,
    OpportunitySummary,
)
from app.services.optimization import OptimizationQueryService

router = APIRouter(tags=["cost optimization"])

OpportunityType = Literal[
    "PRICE_OPTIMIZATION",
    "CONTRACT_LEAKAGE",
    "SUPPLIER_CONSOLIDATION",
    "SUPPLIER_PERFORMANCE",
]
PriorityLevel = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
OpportunityStatus = Literal["OPEN", "IN_REVIEW", "ACCEPTED", "REJECTED", "COMPLETED", "STALE"]
OpportunitySort = Literal["priority_score", "estimated_savings", "review_spend", "created_at"]
SortDirection = Literal["asc", "desc"]


@router.get("/benchmarks", response_model=PaginatedResponse[BenchmarkResponse])
def benchmarks(
    session: DatabaseSession,
    pagination: Pagination,
    category_id: Annotated[int | None, Query(ge=1)] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
) -> PaginatedResponse[BenchmarkResponse]:
    return OptimizationQueryService(session).benchmarks(
        pagination, category_id=category_id, search=search
    )


@router.get(
    "/benchmarks/{item_id}",
    response_model=BenchmarkResponse,
    responses={404: {"model": ErrorResponse}},
)
def benchmark(item_id: int, session: DatabaseSession) -> BenchmarkResponse:
    result = OptimizationQueryService(session).benchmark(item_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BENCHMARK_NOT_FOUND", "message": "Benchmark was not found"},
        )
    return result


@router.get("/opportunities/summary", response_model=OpportunitySummary)
def opportunity_summary(session: DatabaseSession) -> OpportunitySummary:
    return OptimizationQueryService(session).summary()


@router.get("/opportunities", response_model=PaginatedResponse[OpportunityResponse])
def opportunities(
    session: DatabaseSession,
    pagination: Pagination,
    opportunity_type: OpportunityType | None = None,
    priority: PriorityLevel | None = None,
    supplier_id: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
    category_id: Annotated[int | None, Query(ge=1)] = None,
    item_id: Annotated[int | None, Query(ge=1)] = None,
    opportunity_status: OpportunityStatus | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    sort_by: OpportunitySort = "priority_score",
    sort_direction: SortDirection = "desc",
) -> PaginatedResponse[OpportunityResponse]:
    if created_from and created_to and created_from > created_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_DATE_RANGE",
                "message": "created_from cannot be after created_to",
            },
        )
    return OptimizationQueryService(session).opportunities(
        pagination,
        opportunity_type=opportunity_type,
        priority=priority,
        supplier_id=supplier_id,
        category_id=category_id,
        item_id=item_id,
        status=opportunity_status,
        created_from=created_from,
        created_to=created_to,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )


@router.get(
    "/opportunities/{opportunity_id}",
    response_model=OpportunityResponse,
    responses={404: {"model": ErrorResponse}},
)
def opportunity(opportunity_id: int, session: DatabaseSession) -> OpportunityResponse:
    result = OptimizationQueryService(session).opportunity(opportunity_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "OPPORTUNITY_NOT_FOUND", "message": "Opportunity was not found"},
        )
    return result
