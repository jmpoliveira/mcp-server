"""In-memory TicketRepository adapter (mock).

State lives in the process, so it is not shared between container replicas.
Replace it with a database-backed adapter implementing the same port to scale
horizontally.
"""

import asyncio
from collections.abc import Iterable

from src.domain.entities.ticket import Ticket
from src.domain.value_objects.ticket_id import TicketId

_FIRST_NUMBER = 1001


class InMemoryTicketRepository:
    def __init__(self, tickets: Iterable[Ticket] = ()) -> None:
        seeded = list(tickets)
        self._tickets = {ticket.id: ticket for ticket in seeded}
        self._lock = asyncio.Lock()
        self._next_number = (
            max((ticket.id.number for ticket in seeded), default=_FIRST_NUMBER - 1) + 1
        )

    async def get(self, ticket_id: TicketId) -> Ticket | None:
        return self._tickets.get(ticket_id)

    async def next_id(self) -> TicketId:
        async with self._lock:
            ticket_id = TicketId.from_number(self._next_number)
            self._next_number += 1
        return ticket_id

    async def add(self, ticket: Ticket) -> None:
        self._tickets[ticket.id] = ticket
