"""Ticket priority value object."""

from enum import StrEnum

from src.domain.errors import InvalidInputError


class TicketPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

    @classmethod
    def parse(cls, raw: str) -> "TicketPriority":
        """Build a priority from free text, case-insensitively."""
        try:
            return cls(raw.strip().lower())
        except ValueError as err:
            valid = ", ".join(item.value for item in cls)
            raise InvalidInputError(f"priority must be one of: {valid}") from err
