"""MCP tools for tickets. Thin adapter over the use cases."""

import logging
from dataclasses import asdict
from typing import Annotated, Any, Literal

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from src.application.use_cases.create_ticket import CreateTicket
from src.application.use_cases.get_ticket_info import GetTicketInfo
from src.application.use_cases.search_tickets import SearchTickets
from src.interface.mcp.tracing import server_span

logger = logging.getLogger(__name__)

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
# Must list exactly the TicketStatus values (a test checks they do not drift).
# The interface layer repeats them as a Literal so they appear as an enum in the tool schema.
TicketStatusName = Literal["open", "in_progress", "resolved", "closed"]

WRITE = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False
)


def register_ticket_tools(
    server: FastMCP,
    get_ticket_info: GetTicketInfo,
    create_ticket: CreateTicket,
    search_tickets: SearchTickets,
) -> None:
    @server.tool(name="get_ticket_info", annotations=READ_ONLY)
    async def get_ticket_info_tool(
        ticket_id: Annotated[str, Field(description="Ticket id: 'T-' followed by digits.")],
        *,
        ctx: Context,
    ) -> dict[str, Any]:
        """Get one support ticket by its ticket id: title, description, priority,
        status, creation date and the id of the customer it belongs to. It cannot list or
        search tickets, and customer ids ('C-...') are not ticket ids."""
        with server_span(ctx, "get_ticket_info"):
            logger.info("Tool get_ticket_info called")
            return asdict(await get_ticket_info.execute(ticket_id))

    @server.tool(name="search_tickets", annotations=READ_ONLY)
    async def search_tickets_tool(
        customer_id: Annotated[
            str,
            Field(
                description=(
                    "Customer id ('C-' followed by digits), as returned by search_customers."
                )
            ),
        ],
        status: Annotated[
            TicketStatusName | None,
            Field(description="Only tickets with this status. Omit for all statuses."),
        ] = None,
        max_results: Annotated[
            int, Field(description="Maximum number of tickets to return (1-20).")
        ] = 10,
        *,
        ctx: Context,
    ) -> dict[str, Any]:
        """List a customer's support tickets, newest first, optionally filtered by status. Each
        ticket has id, customer_id, title, description, priority, status and creation date. Takes
        a customer id from search_customers. An empty list means the customer exists and has no
        tickets matching the filter."""
        with server_span(ctx, "search_tickets"):
            logger.info("Tool search_tickets called")
            found = await search_tickets.execute(customer_id, status, max_results)
            return {"count": len(found), "tickets": [asdict(item) for item in found]}

    @server.tool(name="create_ticket", annotations=WRITE)
    async def create_ticket_tool(
        customer_id: Annotated[
            str,
            Field(
                description=(
                    "Id of an existing customer as returned by search_customers "
                    "('C-' followed by digits)."
                )
            ),
        ],
        title: Annotated[str, Field(description="Short summary (max 120 characters).")],
        description: Annotated[
            str, Field(description="Full problem description (max 2000 characters).")
        ],
        priority: Annotated[
            Literal["low", "medium", "high", "urgent"],
            Field(description="Ticket priority."),
        ] = "medium",
        *,
        ctx: Context,
    ) -> dict[str, Any]:
        """Create a new support ticket for an existing customer."""
        with server_span(ctx, "create_ticket"):
            logger.info("Tool create_ticket called")
            return asdict(await create_ticket.execute(customer_id, title, description, priority))
