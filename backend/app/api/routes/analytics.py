from fastapi import APIRouter

from app.api.dependencies import CommonAnalyticsFilters, DatabaseSession
from app.schemas.analytics import (
    BusinessUnitAnalyticsItem,
    CategoryAnalyticsItem,
    ContractAnalytics,
    DashboardSummary,
    DeliveryAnalytics,
    MonthlyAnalyticsItem,
    QualityAnalytics,
    SupplierAnalyticsItem,
    SupplierConcentration,
)
from app.services.analytics import AnalyticsService

router = APIRouter(tags=["analytics"])


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(
    session: DatabaseSession, filters: CommonAnalyticsFilters
) -> DashboardSummary:
    return AnalyticsService(session).dashboard_summary(filters)


@router.get("/analytics/spend/suppliers", response_model=list[SupplierAnalyticsItem])
def supplier_analytics(
    session: DatabaseSession, filters: CommonAnalyticsFilters
) -> list[SupplierAnalyticsItem]:
    return AnalyticsService(session).supplier_analytics(filters)


@router.get("/analytics/supplier-concentration", response_model=SupplierConcentration)
def supplier_concentration(
    session: DatabaseSession, filters: CommonAnalyticsFilters
) -> SupplierConcentration:
    return AnalyticsService(session).supplier_concentration(filters)


@router.get("/analytics/spend/categories", response_model=list[CategoryAnalyticsItem])
def category_analytics(
    session: DatabaseSession, filters: CommonAnalyticsFilters
) -> list[CategoryAnalyticsItem]:
    return AnalyticsService(session).category_analytics(filters)


@router.get("/analytics/spend/business-units", response_model=list[BusinessUnitAnalyticsItem])
def business_unit_analytics(
    session: DatabaseSession, filters: CommonAnalyticsFilters
) -> list[BusinessUnitAnalyticsItem]:
    return AnalyticsService(session).business_unit_analytics(filters)


@router.get("/analytics/spend/monthly", response_model=list[MonthlyAnalyticsItem])
def monthly_analytics(
    session: DatabaseSession, filters: CommonAnalyticsFilters
) -> list[MonthlyAnalyticsItem]:
    return AnalyticsService(session).monthly_analytics(filters)


@router.get("/analytics/contract-compliance", response_model=ContractAnalytics)
def contract_analytics(
    session: DatabaseSession, filters: CommonAnalyticsFilters
) -> ContractAnalytics:
    return AnalyticsService(session).contract_analytics(filters)


@router.get("/analytics/quality", response_model=QualityAnalytics)
def quality_analytics(
    session: DatabaseSession, filters: CommonAnalyticsFilters
) -> QualityAnalytics:
    return AnalyticsService(session).quality_analytics(filters)


@router.get("/analytics/delivery", response_model=DeliveryAnalytics)
def delivery_analytics(
    session: DatabaseSession, filters: CommonAnalyticsFilters
) -> DeliveryAnalytics:
    return AnalyticsService(session).delivery_analytics(filters)
