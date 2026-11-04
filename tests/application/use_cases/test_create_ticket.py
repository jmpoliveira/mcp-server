from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.create_ticket import CreateTicket
from src.domain.entities.customer import Customer
from src.domain.errors import InvalidInputError, NotFoundError
from src.domain.value_objects.ticket_id import TicketId


def make_use_case(customer_exists=True):
    tickets = AsyncMock()
    tickets.next_id.return_value = TicketId("T-2000")
    customers = AsyncMock()
    customers.get.return_value = (
        Customer("C-001", "Ann", "a@x.example", "X", "pro") if customer_exists else None
    )
    return CreateTicket(tickets, customers), tickets


async def test_creates_and_persists_an_open_ticket():
    use_case, tickets = make_use_case()

    dto = await use_case.execute(" C-001 ", " Title ", " Details ", "HIGH")

    tickets.add.assert_awaited_once()
    saved = tickets.add.await_args.args[0]
    assert str(saved.id) == "T-2000"
    assert (dto.title, dto.priority, dto.status) == ("Title", "high", "open")


async def test_defaults_to_medium_priority():
    use_case, _ = make_use_case()

    dto = await use_case.execute("C-001", "Title", "Details")

    assert dto.priority == "medium"


async def test_raises_not_found_for_unknown_customer_and_persists_nothing():
    use_case, tickets = make_use_case(customer_exists=False)

    with pytest.raises(NotFoundError, match="C-001"):
        await use_case.execute("C-001", "Title", "Details")

    tickets.add.assert_not_awaited()


@pytest.mark.parametrize(
    ("title", "description", "priority"),
    [
        ("", "Details", "low"),
        ("t" * 121, "Details", "low"),
        ("Title", "", "low"),
        ("Title", "d" * 2001, "low"),
        ("Title", "Details", "critical"),
    ],
)
async def test_rejects_invalid_fields_and_persists_nothing(title, description, priority):
    use_case, tickets = make_use_case()

    with pytest.raises(InvalidInputError):
        await use_case.execute("C-001", title, description, priority)

    tickets.add.assert_not_awaited()
