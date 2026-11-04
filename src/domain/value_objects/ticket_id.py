"""Ticket identifier value object."""

import re
from dataclasses import dataclass

from src.domain.errors import InvalidInputError

_PATTERN = re.compile(r"^T-(\d+)$")


@dataclass(frozen=True, slots=True)
class TicketId:
    """A ticket id such as ``T-1001``. Invalid values cannot be constructed."""

    value: str

    def __post_init__(self) -> None:
        if not _PATTERN.match(self.value):
            raise InvalidInputError("ticket_id must look like 'T-1001'")

    @classmethod
    def parse(cls, raw: str) -> "TicketId":
        """Normalize free text (case and surrounding spaces) into a TicketId."""
        return cls(raw.strip().upper())

    @classmethod
    def from_number(cls, number: int) -> "TicketId":
        return cls(f"T-{number}")

    @property
    def number(self) -> int:
        match = _PATTERN.match(self.value)
        assert match is not None  # guaranteed by __post_init__
        return int(match.group(1))

    def __str__(self) -> str:
        return self.value
