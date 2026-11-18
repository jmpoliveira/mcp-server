"""Use case: list the tickets of one customer."""

import logging

from src.application.dto.ticket_dto import TicketDTO
from src.application.ports.customer_repository import CustomerRepository
from src.application.ports.ticket_repository import TicketRepository
from src.domain.errors import InvalidInputError, NotFoundError
from src.domain.value_objects.ticket_status import TicketStatus

logger = logging.getLogger(__name__)

MAX_RESULTS_LIMIT = 20


class SearchTickets:
    """Filtering, sorting and limiting live here, so a repository only needs a
    simple "tickets of this customer" query."""

    def __init__(self, tickets: TicketRepository, customers: CustomerRepository) -> None:
        self._tickets = tickets
        self._customers = customers

    async def execute(
        self, customer_id: str, status: str | None = None, max_results: int = 10
    ) -> list[TicketDTO]:
        customer_id = customer_id.strip()
        if not customer_id:
            raise InvalidInputError("customer_id must not be empty")
        wanted = TicketStatus.parse(status) if status is not None else None
        limit = max(1, min(max_results, MAX_RESULTS_LIMIT))

        # An unknown customer is an error, never an empty list: an empty list
        # must only ever mean "this customer has no matching tickets".
        if await self._customers.get(customer_id) is None:
            logger.warning("Customer %s not found", customer_id)
            raise NotFoundError(f"Customer {customer_id} not found")

        tickets = await self._tickets.list_by_customer(customer_id)
        if wanted is not None:
            tickets = [ticket for ticket in tickets if ticket.status is wanted]
        # Newest first; the id breaks ties so the order is always deterministic.
        newest_first = sorted(
            tickets, key=lambda ticket: (ticket.created_at, ticket.id.number), reverse=True
        )[:limit]
        logger.info(
            "Ticket search for customer %s returned %d results", customer_id, len(newest_first)
        )
        return [TicketDTO.from_entity(ticket) for ticket in newest_first]
