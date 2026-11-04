"""MCP server assembly (HTTP only)."""

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from config.settings import Settings
from src.application.use_cases.create_ticket import CreateTicket
from src.application.use_cases.get_ticket_info import GetTicketInfo
from src.application.use_cases.search_customers import SearchCustomers
from src.interface.mcp.tools.customer_tools import register_customer_tools
from src.interface.mcp.tools.ticket_tools import register_ticket_tools
from src.interface.mcp.traced_server import TracedFastMCP


def build_server(
    settings: Settings,
    search_customers: SearchCustomers,
    get_ticket_info: GetTicketInfo,
    create_ticket: CreateTicket,
) -> FastMCP:
    """Create the MCP server with its tools and a health endpoint.

    ``stateless_http=True`` keeps no session between requests, so any
    container replica can answer any request.
    """
    server = TracedFastMCP(
        settings.mcp_server_name,
        host=settings.mcp_host,
        port=settings.mcp_port,
        stateless_http=True,
    )

    @server.custom_route("/health", methods=["GET"])
    async def health(_: Request) -> Response:
        return JSONResponse({"status": "ok"})

    register_customer_tools(server, search_customers)
    register_ticket_tools(server, get_ticket_info, create_ticket)
    return server
