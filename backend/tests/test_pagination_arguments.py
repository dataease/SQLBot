"""Guard: out-of-range page/size must not turn a list request into a 500.

``/pager/{pageNum}/{pageSize}`` style routes hand raw path integers to
``PaginationParams``, so ``size=0`` divided by zero while computing
``total_pages`` and ``page=0`` produced a negative OFFSET for the database.
The checks below cover the normalization directly and through
``Paginator.get_paginated_response`` with a stubbed session.
"""

import asyncio

from sqlmodel import Field, SQLModel

from common.core.pagination import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    Paginator,
    normalize_page_args,
)
from common.core.schemas import PaginationParams


class PagedRow(SQLModel, table=True):
    __tablename__ = "pagination_guard_row"

    id: int | None = Field(default=None, primary_key=True)


class _Result:
    def __init__(self, first_value=None):
        self._first = first_value

    def first(self):
        return self._first

    def all(self):
        return []

    def __iter__(self):
        return iter(())


class _Session:
    def __init__(self, total: int):
        self.total = total
        self.statements = []

    def exec(self, stmt):
        self.statements.append(stmt)
        if "count" in str(stmt).lower():
            return _Result(self.total)
        return _Result()


def _paginate(pagination: PaginationParams, total: int = 42):
    paginator = Paginator(_Session(total))
    return asyncio.run(paginator.get_paginated_response(PagedRow, pagination))


def test_normalize_keeps_valid_arguments():
    assert normalize_page_args(3, 40) == (3, 40)


def test_normalize_replaces_out_of_range_arguments():
    assert normalize_page_args(0, 0) == (1, DEFAULT_PAGE_SIZE)
    assert normalize_page_args(-1, -20) == (1, DEFAULT_PAGE_SIZE)
    assert normalize_page_args(1, MAX_PAGE_SIZE + 1) == (1, MAX_PAGE_SIZE)


def test_zero_page_size_does_not_divide_by_zero():
    response = _paginate(PaginationParams(page=1, size=0), total=42)
    assert response.size == DEFAULT_PAGE_SIZE
    assert response.total_pages == 3


def test_negative_page_returns_first_page():
    response = _paginate(PaginationParams(page=0, size=20), total=42)
    assert response.page == 1
    assert response.size == 20
    assert response.total_pages == 3


def test_oversized_page_size_is_bounded():
    response = _paginate(PaginationParams(page=1, size=100000), total=42)
    assert response.size == MAX_PAGE_SIZE
    assert response.total_pages == 1
