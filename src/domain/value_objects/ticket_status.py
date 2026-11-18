"""Ticket status value object."""

from enum import StrEnum

from src.domain.errors import InvalidInputError


class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

    @classmethod
    def parse(cls, raw: str) -> "TicketStatus":
        """Build a status from free text, case-insensitively."""
        try:
            return cls(raw.strip().lower())
        except ValueError as err:
            valid = ", ".join(item.value for item in cls)
            raise InvalidInputError(f"status must be one of: {valid}") from err
