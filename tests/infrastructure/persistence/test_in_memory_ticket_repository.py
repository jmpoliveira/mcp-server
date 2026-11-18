import asyncio
from dataclasses import replace

from src.domain.value_objects.ticket_id import TicketId
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


async def test_list_by_customer_returns_only_that_customers_tickets_including_added_ones():
    repository = InMemoryTicketRepository(TICKETS)
    added = replace(TICKETS[1], id=TicketId("T-2000"), customer_id="C-001")

    await repository.add(added)

    found = await repository.list_by_customer("C-001")
    assert sorted(str(ticket.id) for ticket in found) == ["T-1001", "T-2000"]


async def test_list_by_customer_without_tickets_is_empty():
    assert await InMemoryTicketRepository(TICKETS).list_by_customer("C-004") == []
