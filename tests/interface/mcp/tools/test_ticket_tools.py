from typing import get_args

from src.domain.value_objects.ticket_status import TicketStatus
from src.interface.mcp.tools.ticket_tools import TicketStatusName


def test_status_literal_matches_the_domain_ticket_statuses():
    assert list(get_args(TicketStatusName)) == [status.value for status in TicketStatus]
