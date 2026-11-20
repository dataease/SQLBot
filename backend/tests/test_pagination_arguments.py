"""Guard: out-of-range page/size must not turn a list request into a 500.

``/pager/{pageNum}/{pageSize}`` style routes hand raw path integers to
``PaginationParams``, so ``size=0`` divided by zero while computing
``total_pages`` and ``page=0`` produced a negative OFFSET for the database.
The checks below cover the normalization directly and through
``Paginator.get_paginated_response`` with a stubbed session.
"""

import asyncio

import pytest
from sqlalchemy import event
from sqlmodel import Field, Session, SQLModel, create_engine, select

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


@pytest.mark.parametrize(
    "page,size,expected_page,expected_size,count",
    [
        (1, 20, 1, 20, 20),
        (2, 20, 2, 20, 20),
        (1, 0, 1, 20, 20),
        (0, 20, 1, 20, 20),
        (-1, -20, 1, 20, 20),
        (1, 500, 1, 500, 500),
        (1, 501, 1, 500, 500),
        (1, 1000000, 1, 500, 500),
        (2, 500, 2, 500, 43),
        (3, 500, 3, 500, 0),
        (10**30, 20, 10**30, 20, 0),
    ],
)
def test_real_database_boundaries(page, size, expected_page, expected_size, count):
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    statements = []
    with Session(engine) as session:
        session.add_all(PagedRow(id=i) for i in range(1, 544))
        session.commit()
        event.listen(
            engine,
            "before_cursor_execute",
            lambda conn, cursor, statement, parameters, context, many: (
                statements.append((statement, parameters))
            ),
        )
        response = asyncio.run(
            Paginator(session).get_paginated_response(
                select(PagedRow).order_by(PagedRow.id),
                PaginationParams(page=page, size=size),
            )
        )
        assert (response.page, response.size, response.total) == (
            expected_page,
            expected_size,
            543,
        )
        assert response.total_pages == (543 + expected_size - 1) // expected_size
        assert len(response.items) == count
        if count:
            assert response.items[0]["id"] == (expected_page - 1) * expected_size + 1
            assert statements[-1][1] == (
                expected_size,
                (expected_page - 1) * expected_size,
            )
        else:
            assert len(statements) == 1
    engine.dispose()


def test_direct_paginate_and_empty_database():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        paginator = Paginator(session)
        assert asyncio.run(paginator.paginate(PagedRow, page=10**30, size=0)) == ([], 0)
        response = asyncio.run(
            paginator.get_paginated_response(PagedRow, PaginationParams())
        )
        assert (response.items, response.page, response.size, response.total_pages) == (
            [],
            1,
            20,
            0,
        )
    engine.dispose()
