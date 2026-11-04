import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from src.application.use_cases.create_ticket import CreateTicket
from src.application.use_cases.get_ticket_info import GetTicketInfo
from src.application.use_cases.search_customers import SearchCustomers
from src.infrastructure.persistence.in_memory_customer_repository import (
    InMemoryCustomerRepository,
)
from src.infrastructure.persistence.in_memory_ticket_repository import (
    InMemoryTicketRepository,
)
from src.infrastructure.persistence.mock_data import CUSTOMERS, TICKETS


@pytest.fixture
def customer_repository():
    return InMemoryCustomerRepository(CUSTOMERS)


@pytest.fixture
def ticket_repository():
    return InMemoryTicketRepository(TICKETS)


@pytest.fixture
def use_cases(customer_repository, ticket_repository):
    return (
        SearchCustomers(customer_repository),
        GetTicketInfo(ticket_repository),
        CreateTicket(ticket_repository, customer_repository),
    )


@pytest.fixture(scope="session")
def _span_exporter():
    """Install one global TracerProvider for the whole test session."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return exporter


@pytest.fixture
def span_exporter(_span_exporter):
    """Finished spans of the current test."""
    _span_exporter.clear()
    yield _span_exporter
    _span_exporter.clear()
