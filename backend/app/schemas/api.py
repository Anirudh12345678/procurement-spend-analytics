from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: object | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def create(
        cls, *, items: list[T], total: int, pagination: PaginationParams
    ) -> "PaginatedResponse[T]":
        return cls(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            pages=ceil(total / pagination.page_size) if total else 0,
        )
