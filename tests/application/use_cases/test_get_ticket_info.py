from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.get_ticket_info import GetTicketInfo
from src.domain.entities.ticket import Ticket
from src.domain.errors import InvalidInputError, NotFoundError
from src.domain.value_objects.ticket_id import TicketId
from src.domain.value_objects.ticket_priority import TicketPriority
from src.domain.value_objects.ticket_status import TicketStatus


def sample_ticket():
    return Ticket(
        id=TicketId("T-1001"),
        customer_id="C-001",
        title="Title",
        description="Details",
        priority=TicketPriority.HIGH,
        status=TicketStatus.OPEN,
        created_at=datetime(2026, 10, 28, tzinfo=UTC),
    )


async def test_returns_dto_with_primitive_values():
    repository = AsyncMock()
    repository.get.return_value = sample_ticket()

    dto = await GetTicketInfo(repository).execute("t-1001")

    repository.get.assert_awaited_once_with(TicketId("T-1001"))
    assert (dto.id, dto.priority, dto.status) == ("T-1001", "high", "open")
    assert dto.created_at == "2026-10-28T00:00:00+00:00"


async def test_raises_not_found_when_ticket_is_missing():
    repository = AsyncMock()
    repository.get.return_value = None

    with pytest.raises(NotFoundError, match="T-9999"):
        await GetTicketInfo(repository).execute("T-9999")


async def test_rejects_malformed_id_without_touching_the_repository():
    repository = AsyncMock()

    with pytest.raises(InvalidInputError):
        await GetTicketInfo(repository).execute("../etc/passwd")

    repository.get.assert_not_awaited()
