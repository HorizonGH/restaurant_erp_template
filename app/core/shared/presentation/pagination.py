import math
from collections.abc import Sequence
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)

    @property
    def limit_offset(self) -> tuple[int, int]:
        return self.size, (self.page - 1) * self.size


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(cls, items: Sequence[T], total: int, params: PageParams) -> "Page[T]":
        pages = math.ceil(total / params.size) if params.size else 0
        return cls(
            items=list(items),
            total=total,
            page=params.page,
            size=params.size,
            pages=pages,
        )
