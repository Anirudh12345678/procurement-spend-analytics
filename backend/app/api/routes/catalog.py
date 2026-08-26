from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import DatabaseSession, Pagination
from app.schemas.api import ErrorResponse, PaginatedResponse
from app.schemas.catalog import (
    BusinessUnitResponse,
    CategoryResponse,
    ItemResponse,
    SupplierDetail,
    SupplierListItem,
)
from app.services.catalog import CatalogService

router = APIRouter(tags=["reference data"])


@router.get("/suppliers", response_model=PaginatedResponse[SupplierListItem])
def suppliers(
    session: DatabaseSession,
    pagination: Pagination,
    search: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    country: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
) -> PaginatedResponse[SupplierListItem]:
    return CatalogService(session).suppliers(pagination, search=search, country=country)


@router.get(
    "/suppliers/{supplier_id}",
    response_model=SupplierDetail,
    responses={404: {"model": ErrorResponse}},
)
def supplier(supplier_id: str, session: DatabaseSession) -> SupplierDetail:
    result = CatalogService(session).supplier(supplier_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SUPPLIER_NOT_FOUND", "message": "Supplier was not found"},
        )
    return result


@router.get("/categories", response_model=list[CategoryResponse])
def categories(session: DatabaseSession) -> list[CategoryResponse]:
    return CatalogService(session).categories()


@router.get("/items", response_model=PaginatedResponse[ItemResponse])
def items(
    session: DatabaseSession,
    pagination: Pagination,
    category_id: Annotated[int | None, Query(ge=1)] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
) -> PaginatedResponse[ItemResponse]:
    return CatalogService(session).items(pagination, category_id=category_id, search=search)


@router.get("/business-units", response_model=list[BusinessUnitResponse])
def business_units(session: DatabaseSession) -> list[BusinessUnitResponse]:
    return CatalogService(session).business_units()
