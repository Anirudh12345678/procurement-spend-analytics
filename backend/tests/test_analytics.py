from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BusinessUnit, Category
from app.schemas.analytics import AnalyticsFilters
from app.services.analytics import AnalyticsService


def test_dashboard_summary(analytics_session: Session) -> None:
    result = AnalyticsService(analytics_session).dashboard_summary(AnalyticsFilters())

    assert result.total_spend == Decimal("1000.0000")
    assert result.total_orders == 5
    assert result.average_order_value == Decimal("200.0000")
    assert result.supplier_count == 3
    assert result.category_count == 2
    assert result.business_unit_count == 2


def test_supplier_analytics_and_ranking(analytics_session: Session) -> None:
    results = AnalyticsService(analytics_session).supplier_analytics(AnalyticsFilters())

    assert [result.supplier_id for result in results] == ["SUP-003", "SUP-001", "SUP-002"]
    assert [result.rank for result in results] == [1, 2, 3]
    assert results[0].spend == Decimal("400.0000")
    assert results[0].share_percent == Decimal("40.0000")
    assert results[1].transaction_count == 2
    assert results[1].average_order_value == Decimal("150.0000")
    assert results[1].total_quantity == Decimal("3.0000")
    assert results[1].country == "India"


def test_supplier_concentration_handles_fewer_than_ten_suppliers(
    analytics_session: Session,
) -> None:
    result = AnalyticsService(analytics_session).supplier_concentration(AnalyticsFilters())

    assert result.supplier_count == 3
    assert result.top_5_spend == Decimal("1000.0000")
    assert result.top_5_concentration_percent == Decimal("100.0000")
    assert result.top_10_spend == Decimal("1000.0000")
    assert result.top_10_concentration_percent == Decimal("100.0000")


def test_category_analytics(analytics_session: Session) -> None:
    results = AnalyticsService(analytics_session).category_analytics(AnalyticsFilters())

    assert [result.category_name for result in results] == ["IT", "Office"]
    assert results[0].spend == Decimal("600.0000")
    assert results[0].share_percent == Decimal("60.0000")
    assert results[0].transaction_count == 4
    assert results[0].average_order_value == Decimal("150.0000")
    assert results[0].supplier_count == 2


def test_business_unit_analytics(analytics_session: Session) -> None:
    results = AnalyticsService(analytics_session).business_unit_analytics(AnalyticsFilters())

    assert [result.business_unit_name for result in results] == ["Operations", "Finance"]
    assert results[0].spend == Decimal("600.0000")
    assert results[0].share_percent == Decimal("60.0000")
    assert results[0].transaction_count == 4


def test_monthly_analytics_and_growth(analytics_session: Session) -> None:
    results = AnalyticsService(analytics_session).monthly_analytics(AnalyticsFilters())

    assert len(results) == 2
    assert results[0].month == date(2026, 1, 1)
    assert results[0].spend == Decimal("400.0000")
    assert results[0].transaction_count == 3
    assert results[0].average_order_value == Decimal("133.3333")
    assert results[0].growth_percent is None
    assert results[1].month == date(2026, 2, 1)
    assert results[1].spend == Decimal("600.0000")
    assert results[1].growth_percent == Decimal("50.0000")


def test_contract_analytics(analytics_session: Session) -> None:
    result = AnalyticsService(analytics_session).contract_analytics(AnalyticsFilters())

    assert result.total_spend == Decimal("1000.0000")
    assert result.total_orders == 5
    assert result.on_contract_spend == Decimal("500.0000")
    assert result.off_contract_spend == Decimal("500.0000")
    assert result.on_contract_percent == Decimal("50.0000")
    assert result.off_contract_percent == Decimal("50.0000")
    assert result.on_contract_order_count == 3
    assert result.off_contract_order_count == 2


def test_quality_analytics_and_supplier_rates(analytics_session: Session) -> None:
    result = AnalyticsService(analytics_session).quality_analytics(AnalyticsFilters())

    assert result.total_orders == 5
    assert result.rejected_order_count == 2
    assert result.rejection_rate_percent == Decimal("40.0000")
    assert result.rejected_spend == Decimal("500.0000")
    assert result.suppliers[0].supplier_id == "SUP-003"
    assert result.suppliers[0].rejection_rate_percent == Decimal("100.0000")
    supplier_one = next(item for item in result.suppliers if item.supplier_id == "SUP-001")
    assert supplier_one.rejected_order_count == 1
    assert supplier_one.rejection_rate_percent == Decimal("50.0000")


def test_delivery_analytics_and_average_late_delay(analytics_session: Session) -> None:
    result = AnalyticsService(analytics_session).delivery_analytics(AnalyticsFilters())

    assert result.total_orders == 5
    assert result.late_order_count == 3
    assert result.late_delivery_rate_percent == Decimal("60.0000")
    assert result.average_delay_days == Decimal("3.3333")
    assert result.suppliers[0].supplier_id == "SUP-003"
    assert result.suppliers[0].late_delivery_rate_percent == Decimal("100.0000")
    assert result.suppliers[0].average_delay_days == Decimal("5.0000")


def test_common_filters_apply_to_all_aggregations(analytics_session: Session) -> None:
    service = AnalyticsService(analytics_session)
    february = service.dashboard_summary(
        AnalyticsFilters(date_from=date(2026, 2, 1), date_to=date(2026, 2, 28))
    )
    india = service.dashboard_summary(AnalyticsFilters(country="India"))
    it_category_id = analytics_session.scalar(
        select(Category.category_id).where(Category.category_name == "IT")
    )
    operations_id = analytics_session.scalar(
        select(BusinessUnit.business_unit_id).where(BusinessUnit.business_unit_name == "Operations")
    )
    filtered = service.dashboard_summary(
        AnalyticsFilters(
            supplier_id="SUP-002",
            category_id=it_category_id,
            business_unit_id=operations_id,
            country="United States",
        )
    )

    assert february.total_spend == Decimal("600.0000")
    assert february.total_orders == 2
    assert india.total_spend == Decimal("700.0000")
    assert india.total_orders == 3
    assert filtered.total_spend == Decimal("300.0000")
    assert filtered.total_orders == 2
    assert filtered.supplier_count == 1


def test_empty_filter_result_has_safe_zero_values(analytics_session: Session) -> None:
    service = AnalyticsService(analytics_session)
    filters = AnalyticsFilters(supplier_id="DOES-NOT-EXIST")

    summary = service.dashboard_summary(filters)
    contract = service.contract_analytics(filters)
    delivery = service.delivery_analytics(filters)

    assert summary.total_spend == Decimal("0.0000")
    assert summary.average_order_value == Decimal("0.0000")
    assert contract.on_contract_percent == Decimal("0.0000")
    assert delivery.late_delivery_rate_percent == Decimal("0.0000")
    assert delivery.average_delay_days == Decimal("0.0000")
    assert service.supplier_analytics(filters) == []
    assert service.monthly_analytics(filters) == []
