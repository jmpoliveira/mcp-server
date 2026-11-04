"""Use case: search customers."""

import logging

from src.application.dto.customer_dto import CustomerDTO
from src.application.ports.customer_repository import CustomerRepository
from src.domain.errors import InvalidInputError

logger = logging.getLogger(__name__)

MAX_QUERY_LENGTH = 100
MAX_RESULTS_LIMIT = 20


class SearchCustomers:
    def __init__(self, customers: CustomerRepository) -> None:
        self._customers = customers

    async def execute(self, query: str, max_results: int = 5) -> list[CustomerDTO]:
        cleaned = query.strip()
        if not cleaned:
            raise InvalidInputError("query must not be empty")
        if len(cleaned) > MAX_QUERY_LENGTH:
            raise InvalidInputError(f"query must be at most {MAX_QUERY_LENGTH} characters")
        limit = max(1, min(max_results, MAX_RESULTS_LIMIT))

        found = await self._customers.search(cleaned, limit)
        if found:
            logger.info("Customer search returned %d results", len(found))
        else:
            logger.warning("Customer search returned zero results")
        return [CustomerDTO.from_entity(customer) for customer in found]
