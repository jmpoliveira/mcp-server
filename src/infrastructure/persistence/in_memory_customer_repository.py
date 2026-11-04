"""In-memory CustomerRepository adapter (mock)."""

from collections.abc import Iterable

from src.domain.entities.customer import Customer


class InMemoryCustomerRepository:
    def __init__(self, customers: Iterable[Customer]) -> None:
        self._customers = {customer.id: customer for customer in customers}

    async def search(self, query: str, limit: int) -> list[Customer]:
        needle = query.lower()
        matches = [
            customer
            for customer in self._customers.values()
            if needle in customer.id.lower()
            or needle in customer.name.lower()
            or needle in customer.email.lower()
            or needle in customer.company.lower()
        ]
        return matches[:limit]

    async def get(self, customer_id: str) -> Customer | None:
        return self._customers.get(customer_id)
