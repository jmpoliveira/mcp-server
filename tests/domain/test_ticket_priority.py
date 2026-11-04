import pytest

from src.domain.errors import InvalidInputError
from src.domain.value_objects.ticket_priority import TicketPriority


def test_parse_is_case_insensitive():
    assert TicketPriority.parse(" HIGH ") is TicketPriority.HIGH


def test_parse_rejects_unknown_value_listing_valid_ones():
    with pytest.raises(InvalidInputError, match="low, medium, high, urgent"):
        TicketPriority.parse("critical")
