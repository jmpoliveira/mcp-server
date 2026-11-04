"""End-to-end tracing through the real MCP server, in memory."""

import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import PaginatedRequestParams

from config.settings import Settings
from src.interface.mcp.server import build_server

TRACE_ID = "0af7651916cd43dd8448eb211c80319c"
PARENT_SPAN_ID = "b7ad6b7169203331"
TRACEPARENT = f"00-{TRACE_ID}-{PARENT_SPAN_ID}-01"


@pytest.fixture
def server(use_cases):
    settings = Settings(_env_file=None, mcp_host="127.0.0.1", mcp_port=8000)
    return build_server(settings, *use_cases)


async def call(server, name, arguments, meta=None):
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        return await client.call_tool(name, arguments, meta=meta)


def list_params(traceparent: str) -> PaginatedRequestParams:
    meta = PaginatedRequestParams.Meta.model_validate({"traceparent": traceparent})
    return PaginatedRequestParams(_meta=meta)


def spans_named(exporter, prefix):
    return [span for span in exporter.get_finished_spans() if span.name.startswith(prefix)]


# The SDK client lists tools by itself before the first call_tool of a session
# (to validate the output schema), so these tests select spans by name.
@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("search_customers", {"query": "acme"}),
        ("get_ticket_info", {"ticket_id": "T-1001"}),
        ("create_ticket", {"customer_id": "C-001", "title": "t", "description": "d"}),
    ],
)
async def test_every_tool_continues_the_caller_trace(server, span_exporter, tool, arguments):
    result = await call(server, tool, arguments, meta={"traceparent": TRACEPARENT})

    (span,) = spans_named(span_exporter, "tools/call")
    assert result.isError is False
    assert span.name == f"tools/call {tool}"
    assert format(span.context.trace_id, "032x") == TRACE_ID
    assert format(span.parent.span_id, "016x") == PARENT_SPAN_ID


async def test_tool_call_without_meta_still_works_and_starts_a_trace(server, span_exporter):
    result = await call(server, "get_ticket_info", {"ticket_id": "T-1001"})

    (span,) = spans_named(span_exporter, "tools/call")
    assert result.isError is False
    assert span.parent is None


async def test_domain_error_marks_the_span_as_failed(server, span_exporter):
    result = await call(
        server, "get_ticket_info", {"ticket_id": "T-9999"}, meta={"traceparent": TRACEPARENT}
    )

    (span,) = spans_named(span_exporter, "tools/call")
    assert result.isError is True
    assert span.status.status_code.name == "ERROR"


# ---------------------------------------------------------------- tools/list
async def test_tools_list_continues_the_caller_trace(server, span_exporter):
    params = list_params(TRACEPARENT)
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        listed = await client.list_tools(params=params)

    (span,) = spans_named(span_exporter, "tools/list")
    assert len(listed.tools) == 3
    assert format(span.context.trace_id, "032x") == TRACE_ID
    assert format(span.parent.span_id, "016x") == PARENT_SPAN_ID
    assert span.attributes["mcp.method.name"] == "tools/list"
    assert span.kind.name == "SERVER"


async def test_tools_list_without_meta_starts_a_trace(server, span_exporter):
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        await client.list_tools()

    (span,) = spans_named(span_exporter, "tools/list")
    assert span.parent is None


async def test_an_explicit_list_avoids_the_implicit_one_before_call_tool(server, span_exporter):
    meta = {"traceparent": TRACEPARENT}
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        await client.list_tools(params=list_params(TRACEPARENT))
        await client.call_tool("get_ticket_info", {"ticket_id": "T-1001"}, meta=meta)

    names = [span.name for span in span_exporter.get_finished_spans()]
    assert names == ["tools/list", "tools/call get_ticket_info"]


async def test_call_tool_without_a_prior_list_produces_an_orphan_list_trace(server, span_exporter):
    """Documents SDK behaviour.

    The client lists tools by itself before the first call (no _meta -> orphan root
    trace). The server also refreshes its tool cache while handling the call, and that
    list does carry the caller's trace. Listing explicitly first avoids both.
    """
    await call(
        server, "get_ticket_info", {"ticket_id": "T-1001"}, meta={"traceparent": TRACEPARENT}
    )

    listings = spans_named(span_exporter, "tools/list")
    assert sorted(span.parent is None for span in listings) == [False, True]


async def test_tools_list_log_carries_the_trace_ids(server, span_exporter, caplog):
    from src.infrastructure.logging.filters import TraceContextFilter

    caplog.set_level("INFO", logger="src.interface.mcp.traced_server")
    caplog.handler.addFilter(TraceContextFilter())
    params = list_params(TRACEPARENT)
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        await client.list_tools(params=params)

    (record,) = [r for r in caplog.records if r.getMessage() == "Listed 3 tools"]
    assert record.trace_id == TRACE_ID
