"""Ticket output model of the use cases. Only primitive types."""

from dataclasses import dataclass

from src.domain.entities.ticket import Ticket


@dataclass(frozen=True, slots=True)
class TicketDTO:
    id: str
    customer_id: str
    title: str
    description: str
    priority: str
    status: str
    created_at: str  # ISO 8601

    @classmethod
    def from_entity(cls, ticket: Ticket) -> "TicketDTO":
        return cls(
            id=str(ticket.id),
            customer_id=ticket.customer_id,
            title=ticket.title,
            description=ticket.description,
            priority=ticket.priority.value,
            status=ticket.status.value,
            created_at=ticket.created_at.isoformat(),
        )
