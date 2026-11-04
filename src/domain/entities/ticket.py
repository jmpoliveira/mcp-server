"""Ticket entity with its own business invariants."""

from dataclasses import dataclass
from datetime import datetime

from src.domain.errors import InvalidInputError
from src.domain.value_objects.ticket_id import TicketId
from src.domain.value_objects.ticket_priority import TicketPriority
from src.domain.value_objects.ticket_status import TicketStatus

MAX_TITLE_LENGTH = 120
MAX_DESCRIPTION_LENGTH = 2000


@dataclass(frozen=True, slots=True)
class Ticket:
    id: TicketId
    customer_id: str
    title: str
    description: str
    priority: TicketPriority
    status: TicketStatus
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.title or len(self.title) > MAX_TITLE_LENGTH:
            raise InvalidInputError(f"title must have between 1 and {MAX_TITLE_LENGTH} characters")
        if not self.description or len(self.description) > MAX_DESCRIPTION_LENGTH:
            raise InvalidInputError(
                f"description must have between 1 and {MAX_DESCRIPTION_LENGTH} characters"
            )

    @classmethod
    def open_new(
        cls,
        *,
        id: TicketId,
        customer_id: str,
        title: str,
        description: str,
        priority: TicketPriority,
        created_at: datetime,
    ) -> "Ticket":
        """Create a ticket in its initial ``open`` state."""
        return cls(
            id=id,
            customer_id=customer_id,
            title=title,
            description=description,
            priority=priority,
            status=TicketStatus.OPEN,
            created_at=created_at,
        )
