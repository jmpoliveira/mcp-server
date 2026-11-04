import asyncio

from src.infrastructure.persistence.in_memory_ticket_repository import (
    InMemoryTicketRepository,
)
from src.infrastructure.persistence.mock_data import TICKETS


async def test_next_id_continues_after_the_highest_seeded_id():
    repository = InMemoryTicketRepository(TICKETS)

    first = await repository.next_id()
    second = await repository.next_id()

    assert (str(first), str(second)) == ("T-1004", "T-1005")


async def test_next_id_on_empty_repository_starts_at_1001():
    assert str(await InMemoryTicketRepository().next_id()) == "T-1001"


async def test_concurrent_next_id_calls_never_collide():
    repository = InMemoryTicketRepository()

    ids = await asyncio.gather(*(repository.next_id() for _ in range(50)))

    assert len(set(ids)) == 50


async def test_added_ticket_can_be_fetched():
    repository = InMemoryTicketRepository(TICKETS)
    ticket = TICKETS[0]

    await repository.add(ticket)

    assert await repository.get(ticket.id) == ticket
