"""Customer entity."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Customer:
    id: str
    name: str
    email: str
    company: str
    plan: str
