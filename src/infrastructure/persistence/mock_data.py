"""Seed data for the in-memory (mock) repositories."""

from datetime import UTC, datetime

from src.domain.entities.customer import Customer
from src.domain.entities.ticket import Ticket
from src.domain.value_objects.ticket_id import TicketId
from src.domain.value_objects.ticket_priority import TicketPriority
from src.domain.value_objects.ticket_status import TicketStatus

CUSTOMERS = [
    Customer("C-001", "Alice Johnson", "alice.johnson@acme.example", "Acme Corp", "enterprise"),
    Customer("C-002", "Bruno Costa", "bruno.costa@globex.example", "Globex", "pro"),
    Customer("C-003", "Carla Mendes", "carla.mendes@initech.example", "Initech", "free"),
    Customer("C-004", "David Lee", "david.lee@acme.example", "Acme Corp", "enterprise"),
]

TICKETS = [
    Ticket(
        id=TicketId("T-1001"),
        customer_id="C-001",
        title="Cannot export monthly report",
        description="The export button returns an error for reports above 10k rows.",
        priority=TicketPriority.HIGH,
        status=TicketStatus.IN_PROGRESS,
        created_at=datetime(2026, 10, 28, 9, 30, tzinfo=UTC),
    ),
    Ticket(
        id=TicketId("T-1002"),
        customer_id="C-002",
        title="Invoice shows wrong VAT",
        description="The October invoice applies 23% VAT instead of 0%.",
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.OPEN,
        created_at=datetime(2026, 10, 30, 14, 5, tzinfo=UTC),
    ),
    Ticket(
        id=TicketId("T-1003"),
        customer_id="C-003",
        title="Password reset email not received",
        description="Reset emails never arrive, spam folder checked.",
        priority=TicketPriority.LOW,
        status=TicketStatus.RESOLVED,
        created_at=datetime(2026, 10, 12, 8, 0, tzinfo=UTC),
    ),
]
