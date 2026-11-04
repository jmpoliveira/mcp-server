from src.infrastructure.persistence.in_memory_customer_repository import (
    InMemoryCustomerRepository,
)
from src.infrastructure.persistence.mock_data import CUSTOMERS


async def test_search_matches_company_case_insensitively():
    repository = InMemoryCustomerRepository(CUSTOMERS)

    result = await repository.search("ACME", limit=10)

    assert {customer.id for customer in result} == {"C-001", "C-004"}


async def test_search_respects_limit():
    repository = InMemoryCustomerRepository(CUSTOMERS)

    assert len(await repository.search("example", limit=2)) == 2


async def test_get_returns_none_for_unknown_id():
    assert await InMemoryCustomerRepository(CUSTOMERS).get("C-999") is None
