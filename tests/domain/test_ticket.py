from datetime import UTC, datetime

import pytest

from src.domain.entities.ticket import Ticket
from src.domain.errors import InvalidInputError
from src.domain.value_objects.ticket_id import TicketId
from src.domain.value_objects.ticket_priority import TicketPriority
from src.domain.value_objects.ticket_status import TicketStatus

NOW = datetime(2026, 11, 3, tzinfo=UTC)


def make(title="Title", description="Details"):
    return Ticket.open_new(
        id=TicketId("T-1"),
        customer_id="C-001",
        title=title,
        description=description,
        priority=TicketPriority.LOW,
        created_at=NOW,
    )


def test_open_new_starts_in_open_status():
    assert make().status is TicketStatus.OPEN


@pytest.mark.parametrize(
    ("title", "description"),
    [("", "d"), ("t" * 121, "d"), ("t", ""), ("t", "d" * 2001)],
)
def test_rejects_invalid_title_or_description(title, description):
    with pytest.raises(InvalidInputError):
        make(title, description)
