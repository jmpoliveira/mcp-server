"""FastMCP with tracing for the requests the SDK handles by itself."""

import inspect
import logging
from collections.abc import Callable
from typing import Any

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

    It also normalises tool descriptions taken from docstrings (see ``add_tool``).
    """

    def add_tool(
        self, fn: Callable[..., Any], *args: Any, description: str | None = None, **kwargs: Any
    ) -> None:
        """Register a tool whose description does not depend on the Python version.

        Without an explicit description FastMCP uses the raw docstring. Python 3.13+
        removes the docstring indentation at compile time and 3.12 keeps it, so a
        multi-line docstring would reach the model (and the stored examples)
        differently on each version. ``inspect.cleandoc`` gives the same text on all.
        """
        if description is None and fn.__doc__:
            description = inspect.cleandoc(fn.__doc__)
        super().add_tool(fn, *args, description=description, **kwargs)

    async def list_tools(self) -> list[MCPTool]:
        with method_span(self.get_context(), "tools/list"):
            tools = await super().list_tools()
            # Logged inside the span so the line carries trace_id and span_id.
            logger.info("Listed %d tools", len(tools))
            return tools
