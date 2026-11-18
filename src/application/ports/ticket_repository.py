"""Port: what the use cases need from ticket storage."""

from typing import Protocol

from src.domain.entities.ticket import Ticket
from src.domain.value_objects.ticket_id import TicketId


class TicketRepository(Protocol):
    async def get(self, ticket_id: TicketId) -> Ticket | None: ...

    async def next_id(self) -> TicketId:
        """Reserve and return a new unique ticket id."""
        ...

    async def list_by_customer(self, customer_id: str) -> list[Ticket]:
        """Return every ticket of one customer, in no particular order."""
        ...

    async def add(self, ticket: Ticket) -> None:
        """Persist a ticket."""
        ...
