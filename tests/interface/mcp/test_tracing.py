from types import SimpleNamespace
from unittest.mock import MagicMock, PropertyMock

import pytest
from opentelemetry.trace import SpanKind, StatusCode

from src.interface.mcp.tracing import extract_parent_context, server_span

TRACE_ID = "0af7651916cd43dd8448eb211c80319c"
PARENT_SPAN_ID = "b7ad6b7169203331"
TRACEPARENT = f"00-{TRACE_ID}-{PARENT_SPAN_ID}-01"


def make_ctx(meta):
    ctx = MagicMock()
    ctx.request_context.meta = meta
    return ctx


def test_extract_returns_a_context_for_a_valid_traceparent():
    ctx = make_ctx(SimpleNamespace(traceparent=TRACEPARENT))

    assert extract_parent_context(ctx) is not None


@pytest.mark.parametrize(
    "meta",
    [
        None,
        SimpleNamespace(),
        SimpleNamespace(traceparent=123),
        SimpleNamespace(traceparent="garbage"),
    ],
)
def test_extract_returns_none_when_there_is_no_usable_context(meta):
    assert extract_parent_context(make_ctx(meta)) is None


def test_extract_returns_none_outside_of_a_request():
    ctx = MagicMock()
    type(ctx).request_context = PropertyMock(side_effect=ValueError)

    assert extract_parent_context(ctx) is None


def test_span_continues_the_received_trace(span_exporter):
    ctx = make_ctx(SimpleNamespace(traceparent=TRACEPARENT))

    with server_span(ctx, "get_ticket_info"):
        pass

    (span,) = span_exporter.get_finished_spans()
    assert span.name == "tools/call get_ticket_info"
    assert span.kind is SpanKind.SERVER
    assert format(span.context.trace_id, "032x") == TRACE_ID
    assert format(span.parent.span_id, "016x") == PARENT_SPAN_ID
    assert span.attributes["mcp.tool.name"] == "get_ticket_info"
    assert span.attributes["mcp.method.name"] == "tools/call"


def test_span_starts_a_new_trace_without_context(span_exporter):
    with server_span(make_ctx(None), "create_ticket"):
        pass

    (span,) = span_exporter.get_finished_spans()
    assert span.parent is None


def test_span_records_the_error_and_reraises(span_exporter):
    with pytest.raises(ValueError, match="boom"):
        with server_span(make_ctx(None), "create_ticket"):
            raise ValueError("boom")

    (span,) = span_exporter.get_finished_spans()
    assert span.status.status_code is StatusCode.ERROR
    assert span.events[0].name == "exception"


def test_method_span_names_the_method_and_continues_the_trace(span_exporter):
    from src.interface.mcp.tracing import method_span

    ctx = make_ctx(SimpleNamespace(traceparent=TRACEPARENT))

    with method_span(ctx, "tools/list"):
        pass

    (span,) = span_exporter.get_finished_spans()
    assert span.name == "tools/list"
    assert span.kind is SpanKind.SERVER
    assert "mcp.tool.name" not in span.attributes
    assert format(span.parent.span_id, "016x") == PARENT_SPAN_ID
