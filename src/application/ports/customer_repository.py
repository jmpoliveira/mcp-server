"""Port: what the use cases need from customer storage."""

from typing import Protocol

from src.domain.entities.customer import Customer


class CustomerRepository(Protocol):
    async def search(self, query: str, limit: int) -> list[Customer]: ...

    async def get(self, customer_id: str) -> Customer | None: ...
