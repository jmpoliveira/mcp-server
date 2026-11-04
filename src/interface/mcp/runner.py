"""Run the MCP server over HTTP with uvicorn, logging through our own pipeline."""

import uvicorn
from mcp.server.fastmcp import FastMCP

from config.settings import Settings


def run_http(server: FastMCP, settings: Settings) -> None:
    """Serve the streamable HTTP app and block until the server stops.

    ``FastMCP.run`` would let uvicorn install its own logging config, with
    plain-text handlers that bypass ours. ``log_config=None`` keeps uvicorn's
    loggers propagating to the root logger, so every line on stdout is JSON in
    the json format. ``log_level`` is deliberately not passed: uvicorn would
    override the levels set in logging.json.
    """
    config = uvicorn.Config(
        server.streamable_http_app(),
        host=settings.mcp_host,
        port=settings.mcp_port,
        log_config=None,
    )
    uvicorn.Server(config).run()
