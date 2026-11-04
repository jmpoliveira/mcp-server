"""OpenTelemetry helpers for the MCP interface layer.

The caller (for example simple-ai-agent) sends its W3C trace context inside the
``_meta`` field of the MCP message. Reading it from there, instead of from HTTP
headers, keeps each request attached to the span that issued it: the MCP
client sends every request from a long-lived task, so a header injected by an
HTTP instrumentation would carry the context captured when the connection was
opened. ``_meta`` also works over transports without headers, such as stdio.

When ``_meta`` carries no trace context, the span falls back to the current
context, which an optional ASGI middleware may have populated from the HTTP
``traceparent`` header. Without either, a new trace is started.

This module is the only place in the server that knows about OpenTelemetry
context propagation, so ``domain`` and ``application`` stay free of it.
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from mcp.server.fastmcp import Context
from opentelemetry import propagate, trace
from opentelemetry.context import Context as OtelContext
from opentelemetry.trace import Span, SpanKind

logger = logging.getLogger(__name__)

TRACER_NAME = "mcp-server.interface"
_CARRIER_KEYS = ("traceparent", "tracestate", "baggage")


def extract_parent_context(ctx: Context) -> OtelContext | None:
    """Return the trace context carried in the request ``_meta``, if any.

    Returns ``None`` when the request has no usable context, so the caller can
    fall back to the current one. Invalid ``traceparent`` values are ignored.
    """
    try:
        meta = ctx.request_context.meta
    except ValueError:  # called outside of an MCP request
        logger.debug("No active MCP request, skipping trace context extraction")
        return None
    if meta is None:
        return None

    carrier = {
        key: value for key in _CARRIER_KEYS if isinstance(value := getattr(meta, key, None), str)
    }
    if "traceparent" not in carrier:
        return None

    parent = propagate.extract(carrier)
    if not trace.get_current_span(parent).get_span_context().is_valid:
        logger.warning("Ignoring invalid traceparent received in request _meta")
        return None
    return parent


@contextmanager
def _server_span(ctx: Context, span_name: str, attributes: dict[str, str]) -> Iterator[Span]:
    tracer = trace.get_tracer(TRACER_NAME)
    parent = extract_parent_context(ctx)
    with tracer.start_as_current_span(span_name, context=parent, kind=SpanKind.SERVER) as span:
        span.set_attributes(attributes)
        yield span


@contextmanager
def server_span(ctx: Context, tool_name: str) -> Iterator[Span]:
    """Run a block inside a SERVER span for an MCP ``tools/call`` request.

    Exceptions are recorded on the span, mark it as an error, and propagate.
    """
    with _server_span(
        ctx,
        f"tools/call {tool_name}",
        {"mcp.method.name": "tools/call", "mcp.tool.name": tool_name},
    ) as span:
        yield span


@contextmanager
def method_span(ctx: Context, method: str) -> Iterator[Span]:
    """Run a block inside a SERVER span for an MCP request without a tool name.

    Used for requests such as ``tools/list``.
    """
    with _server_span(ctx, method, {"mcp.method.name": method}) as span:
        yield span
