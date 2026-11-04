import pytest

from src.domain.errors import InvalidInputError
from src.domain.value_objects.ticket_id import TicketId


def test_parse_normalizes_case_and_spaces():
    assert TicketId.parse("  t-1002 ") == TicketId("T-1002")


def test_number_returns_the_numeric_part():
    assert TicketId("T-1042").number == 1042


def test_from_number_round_trips():
    assert str(TicketId.from_number(7)) == "T-7"


@pytest.mark.parametrize("raw", ["", "1001", "T-abc", "T-", "../etc/passwd"])
def test_rejects_malformed_ids(raw):
    with pytest.raises(InvalidInputError):
        TicketId.parse(raw)
