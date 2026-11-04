"""FastMCP with tracing for the requests the SDK handles by itself."""

import logging

from mcp.server.fastmcp import FastMCP
from mcp.types import Tool as MCPTool

from src.interface.mcp.tracing import method_span

logger = logging.getLogger(__name__)


class TracedFastMCP(FastMCP):
    """FastMCP that traces ``tools/list``.

    ``tools/call`` is traced inside each tool (it needs the tool name and the
    result of the use case). ``tools/list`` has no tool code of ours, so it is
    traced here. An agent calls it at the start of every run, so without this
    span the discovery step would be missing from the trace.
    """

    async def list_tools(self) -> list[MCPTool]:
        with method_span(self.get_context(), "tools/list"):
            tools = await super().list_tools()
            # Logged inside the span so the line carries trace_id and span_id.
            logger.info("Listed %d tools", len(tools))
            return tools
