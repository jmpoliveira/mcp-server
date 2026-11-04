"""Use case: get a ticket by id."""

import logging

from src.application.dto.ticket_dto import TicketDTO
from src.application.ports.ticket_repository import TicketRepository
from src.domain.errors import NotFoundError
from src.domain.value_objects.ticket_id import TicketId

logger = logging.getLogger(__name__)


class GetTicketInfo:
    def __init__(self, tickets: TicketRepository) -> None:
        self._tickets = tickets

    async def execute(self, ticket_id: str) -> TicketDTO:
        parsed = TicketId.parse(ticket_id)
        ticket = await self._tickets.get(parsed)
        if ticket is None:
            logger.warning("Ticket %s not found", parsed)
            raise NotFoundError(f"Ticket {parsed} not found")
        return TicketDTO.from_entity(ticket)
