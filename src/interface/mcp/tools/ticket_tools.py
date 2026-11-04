"""MCP tools for tickets. Thin adapter over the use cases."""

import logging
from dataclasses import asdict
from typing import Annotated, Any, Literal

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from src.application.use_cases.create_ticket import CreateTicket
from src.application.use_cases.get_ticket_info import GetTicketInfo
from src.interface.mcp.tracing import server_span

logger = logging.getLogger(__name__)

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
WRITE = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False
)


def register_ticket_tools(
    server: FastMCP, get_ticket_info: GetTicketInfo, create_ticket: CreateTicket
) -> None:
    @server.tool(name="get_ticket_info", annotations=READ_ONLY)
    async def get_ticket_info_tool(
        ticket_id: Annotated[str, Field(description="Ticket identifier, for example 'T-1001'.")],
        *,
        ctx: Context,
    ) -> dict[str, Any]:
        """Get the details and current status of a support ticket."""
        with server_span(ctx, "get_ticket_info"):
            logger.info("Tool get_ticket_info called")
            return asdict(await get_ticket_info.execute(ticket_id))

    @server.tool(name="create_ticket", annotations=WRITE)
    async def create_ticket_tool(
        customer_id: Annotated[
            str, Field(description="Id of an existing customer, for example 'C-001'.")
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
