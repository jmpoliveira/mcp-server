from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.search_customers import SearchCustomers
from src.domain.entities.customer import Customer
from src.domain.errors import InvalidInputError


async def test_returns_dtos_for_matching_customers():
    # Arrange
    repository = AsyncMock()
    repository.search.return_value = [Customer("C-1", "Ann", "a@x.example", "X", "pro")]

    # Act
    result = await SearchCustomers(repository).execute("ann")

    # Assert
    assert [item.id for item in result] == ["C-1"]


async def test_returns_empty_list_when_nothing_matches():
    repository = AsyncMock()
    repository.search.return_value = []

    assert await SearchCustomers(repository).execute("zzz") == []


@pytest.mark.parametrize("query", ["", "   ", "x" * 101])
async def test_rejects_invalid_query_without_touching_the_repository(query):
    repository = AsyncMock()

    with pytest.raises(InvalidInputError):
        await SearchCustomers(repository).execute(query)

    repository.search.assert_not_awaited()


@pytest.mark.parametrize(("requested", "expected"), [(0, 1), (-5, 1), (999, 20)])
async def test_clamps_the_result_limit(requested, expected):
    repository = AsyncMock()
    repository.search.return_value = []

    await SearchCustomers(repository).execute(" acme ", max_results=requested)

    repository.search.assert_awaited_once_with("acme", expected)
