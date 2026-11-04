"""Domain errors. Pure Python, no framework dependencies."""


class DomainError(Exception):
    """Base class for expected, business-level errors."""


class NotFoundError(DomainError):
    """A requested entity does not exist."""


class InvalidInputError(DomainError):
    """The caller supplied invalid input."""
