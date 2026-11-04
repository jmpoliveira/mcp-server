"""MCP tools for customers. Thin adapter over the use cases."""

import logging
from dataclasses import asdict
from typing import Annotated, Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from src.application.use_cases.search_customers import SearchCustomers
from src.interface.mcp.tracing import server_span

logger = logging.getLogger(__name__)

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)


def register_customer_tools(server: FastMCP, search_customers: SearchCustomers) -> None:
    @server.tool(name="search_customers", annotations=READ_ONLY)
    async def search_customers_tool(
        query: Annotated[
            str, Field(description="Text to match against id, name, email or company.")
        ],
        max_results: Annotated[
            int, Field(description="Maximum number of customers to return (1-20).")
        ] = 5,
        *,
        ctx: Context,
    ) -> dict[str, Any]:
        """Search customer records by id, name, email or company."""
        with server_span(ctx, "search_customers"):
            logger.info("Tool search_customers called")
            found = await search_customers.execute(query, max_results)
            return {"count": len(found), "customers": [asdict(item) for item in found]}
