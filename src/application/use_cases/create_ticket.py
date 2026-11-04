"""Use case: create a ticket for an existing customer."""

import logging
from datetime import UTC, datetime

from src.application.dto.ticket_dto import TicketDTO
from src.application.ports.customer_repository import CustomerRepository
from src.application.ports.ticket_repository import TicketRepository
from src.domain.entities.ticket import Ticket
from src.domain.errors import NotFoundError
from src.domain.value_objects.ticket_priority import TicketPriority

logger = logging.getLogger(__name__)


class CreateTicket:
    def __init__(self, tickets: TicketRepository, customers: CustomerRepository) -> None:
        self._tickets = tickets
        self._customers = customers

    async def execute(
        self,
        customer_id: str,
        title: str,
        description: str,
        priority: str = "medium",
    ) -> TicketDTO:
        parsed_priority = TicketPriority.parse(priority)
        customer_id = customer_id.strip()
        if await self._customers.get(customer_id) is None:
            raise NotFoundError(f"Customer {customer_id} not found")

        ticket = Ticket.open_new(
            id=await self._tickets.next_id(),
            customer_id=customer_id,
            title=title.strip(),
            description=description.strip(),
            priority=parsed_priority,
            created_at=datetime.now(UTC),
        )
        await self._tickets.add(ticket)
        logger.info("Ticket %s created for customer %s", ticket.id, customer_id)
        return TicketDTO.from_entity(ticket)
