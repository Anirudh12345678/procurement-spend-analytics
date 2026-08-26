from typing import Literal

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import (
    DatabaseSession,
    Pagination,
    RecommendationClient,
)
from app.schemas.api import ErrorResponse, PaginatedResponse
from app.schemas.recommendations import (
    GenerateRecommendationRequest,
    RecommendationResponse,
)
from app.services.recommendations import RecommendationService

router = APIRouter(tags=["AI procurement advisor"])

OpportunityType = Literal[
    "PRICE_OPTIMIZATION",
    "CONTRACT_LEAKAGE",
    "SUPPLIER_CONSOLIDATION",
    "SUPPLIER_PERFORMANCE",
]


@router.post(
    "/recommendations/generate",
    response_model=RecommendationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}},
)
def generate_recommendation(
    request: GenerateRecommendationRequest,
    session: DatabaseSession,
    client: RecommendationClient,
) -> RecommendationResponse:
    service = RecommendationService(session)
    stored = service.generate(request.opportunity_id, client=client, force=request.force)
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "OPPORTUNITY_NOT_FOUND",
                "message": "Opportunity was not found",
            },
        )
    result = service.recommendation(stored.recommendation_id)
    assert result is not None
    return result


@router.get("/recommendations", response_model=PaginatedResponse[RecommendationResponse])
def recommendations(
    session: DatabaseSession,
    pagination: Pagination,
    opportunity_type: OpportunityType | None = None,
) -> PaginatedResponse[RecommendationResponse]:
    return RecommendationService(session).recommendations(
        pagination, opportunity_type=opportunity_type
    )


@router.get(
    "/recommendations/{recommendation_id}",
    response_model=RecommendationResponse,
    responses={404: {"model": ErrorResponse}},
)
def recommendation(recommendation_id: int, session: DatabaseSession) -> RecommendationResponse:
    result = RecommendationService(session).recommendation(recommendation_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "RECOMMENDATION_NOT_FOUND",
                "message": "Recommendation was not found",
            },
        )
    return result
