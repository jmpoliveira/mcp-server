"""Entry point and composition root: the only place that knows every layer."""

import logging
import signal
from types import FrameType

from mcp.server.fastmcp import FastMCP

from config.settings import Settings, get_settings
from src.application.use_cases.create_ticket import CreateTicket
from src.application.use_cases.get_ticket_info import GetTicketInfo
from src.application.use_cases.search_customers import SearchCustomers
from src.infrastructure.logging.setup import setup_logging, shutdown_logging
from src.infrastructure.persistence.in_memory_customer_repository import (
    InMemoryCustomerRepository,
)
from src.infrastructure.persistence.in_memory_ticket_repository import (
    InMemoryTicketRepository,
)
from src.infrastructure.persistence.mock_data import CUSTOMERS, TICKETS
from src.infrastructure.telemetry import setup_tracing, shutdown_tracing
from src.interface.mcp.runner import run_http
from src.interface.mcp.server import build_server

logger = logging.getLogger(__name__)


def build_application(settings: Settings) -> FastMCP:
    """Wire adapters -> use cases -> server. Swap the repositories here."""
    customers = InMemoryCustomerRepository(CUSTOMERS)
    tickets = InMemoryTicketRepository(TICKETS)

    return build_server(
        settings,
        SearchCustomers(customers),
        GetTicketInfo(tickets),
        CreateTicket(tickets, customers),
    )


def exit_on_sigterm(signum: int, frame: FrameType | None) -> None:
    """Turn SIGTERM (sent by ``docker stop``) into a normal interpreter exit.

    uvicorn restores the previous handler and re-raises SIGTERM after a graceful
    stop. With the default action the process would die before the ``finally``
    block below could flush pending spans and logs.
    """
    logger.warning("Received %s, shutting down", signal.Signals(signum).name)
    raise SystemExit(0)


def main() -> None:
    signal.signal(signal.SIGTERM, exit_on_sigterm)
    settings = get_settings()
    setup_logging(settings)  # before FastMCP is created
    tracing = setup_tracing(settings)
    try:
        server = build_application(settings)
        logger.info(
            "Starting MCP server on %s:%d (endpoint /mcp)",
            settings.mcp_host,
            settings.mcp_port,
        )
        run_http(server, settings)
    except KeyboardInterrupt:
        # Ctrl+C: uvicorn already stopped gracefully and re-raised the signal.
        logger.info("Interrupted by user (Ctrl+C), server stopped")
    finally:
        shutdown_tracing(tracing)
        shutdown_logging()  # last, so the shutdown messages above are flushed


if __name__ == "__main__":
    main()
