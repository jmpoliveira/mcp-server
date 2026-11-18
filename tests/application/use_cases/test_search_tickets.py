from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.search_tickets import SearchTickets
from src.domain.entities.customer import Customer
from src.domain.entities.ticket import Ticket
from src.domain.errors import InvalidInputError, NotFoundError
from src.domain.value_objects.ticket_id import TicketId
from src.domain.value_objects.ticket_priority import TicketPriority
from src.domain.value_objects.ticket_status import TicketStatus

START = datetime(2026, 1, 1, tzinfo=UTC)


def make_ticket(number, *, days, status=TicketStatus.OPEN, customer_id="C-001"):
    return Ticket(
        id=TicketId.from_number(number),
        customer_id=customer_id,
        title=f"Ticket {number}",
        description="Details",
        priority=TicketPriority.MEDIUM,
        status=status,
        created_at=START + timedelta(days=days),
    )


def make_use_case(tickets=(), *, customer_exists=True):
    ticket_repository = AsyncMock()
    ticket_repository.list_by_customer.return_value = list(tickets)
    customer_repository = AsyncMock()
    customer_repository.get.return_value = (
        Customer("C-001", "Ann", "a@x.example", "X", "pro") if customer_exists else None
    )
    return SearchTickets(ticket_repository, customer_repository), ticket_repository


def ids(dtos):
    return [dto.id for dto in dtos]


async def test_returns_the_customers_tickets_newest_first():
    use_case, repository = make_use_case(
        [make_ticket(1, days=1), make_ticket(2, days=3), make_ticket(3, days=2)]
    )

    result = await use_case.execute("C-001")

    repository.list_by_customer.assert_awaited_once_with("C-001")
    assert ids(result) == ["T-2", "T-3", "T-1"]


async def test_tickets_created_at_the_same_time_are_ordered_by_id_descending():
    use_case, _ = make_use_case([make_ticket(1, days=0), make_ticket(2, days=0)])

    assert ids(await use_case.execute("C-001")) == ["T-2", "T-1"]


async def test_filters_by_status_case_insensitively():
    use_case, _ = make_use_case(
        [
            make_ticket(1, days=1, status=TicketStatus.RESOLVED),
            make_ticket(2, days=2, status=TicketStatus.OPEN),
        ]
    )

    result = await use_case.execute("C-001", status=" Resolved ")

    assert ids(result) == ["T-1"]


async def test_status_filter_with_no_match_is_an_empty_list():
    use_case, _ = make_use_case([make_ticket(1, days=1)])

    assert await use_case.execute("C-001", status="closed") == []


@pytest.mark.parametrize(("max_results", "expected"), [(0, 1), (-5, 1), (2, 2), (50, 20)])
async def test_max_results_is_clamped_between_1_and_20(max_results, expected):
    use_case, _ = make_use_case([make_ticket(n, days=n) for n in range(1, 31)])

    result = await use_case.execute("C-001", max_results=max_results)

    assert len(result) == expected


async def test_defaults_to_ten_results():
    use_case, _ = make_use_case([make_ticket(n, days=n) for n in range(1, 16)])

    assert len(await use_case.execute("C-001")) == 10


async def test_customer_without_tickets_is_an_empty_list():
    use_case, _ = make_use_case([])

    assert await use_case.execute("C-001") == []


async def test_unknown_customer_raises_not_found_instead_of_an_empty_list():
    use_case, repository = make_use_case(customer_exists=False)

    with pytest.raises(NotFoundError, match="Customer C-404 not found"):
        await use_case.execute("C-404")

    repository.list_by_customer.assert_not_awaited()


@pytest.mark.parametrize("customer_id", ["", "   "])
async def test_blank_customer_id_is_rejected(customer_id):
    use_case, repository = make_use_case()

    with pytest.raises(InvalidInputError, match="customer_id must not be empty"):
        await use_case.execute(customer_id)

    repository.list_by_customer.assert_not_awaited()


async def test_invalid_status_is_rejected_listing_the_allowed_values():
    use_case, repository = make_use_case()

    with pytest.raises(InvalidInputError, match="open, in_progress, resolved, closed"):
        await use_case.execute("C-001", status="pending")

    repository.list_by_customer.assert_not_awaited()


async def test_customer_id_is_trimmed():
    use_case, repository = make_use_case([make_ticket(1, days=1)])

    await use_case.execute("  C-001 ")

    repository.list_by_customer.assert_awaited_once_with("C-001")
