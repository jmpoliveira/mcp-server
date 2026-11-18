import pytest

from src.domain.errors import InvalidInputError
from src.domain.value_objects.ticket_status import TicketStatus


def test_parse_is_case_insensitive_and_trims():
    assert TicketStatus.parse(" In_Progress ") is TicketStatus.IN_PROGRESS


def test_parse_rejects_unknown_value_listing_valid_ones():
    with pytest.raises(InvalidInputError, match="open, in_progress, resolved, closed"):
        TicketStatus.parse("pending")
