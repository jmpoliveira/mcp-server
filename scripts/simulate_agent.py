"""Simulate an agent calling the MCP server, to test tracing without simple-ai-agent.

Creates a root span ``agent.run``, one child span for the tools listing and one per tool
call, and sends the trace context to the server inside the request ``_meta``.

Usage:
    OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \\
        python scripts/simulate_agent.py --url http://localhost:3000/mcp
"""

import argparse
import asyncio
import os
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import PaginatedRequestParams, TextContent
from opentelemetry import propagate, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

SERVICE = "simulated-agent"


def build_provider() -> TracerProvider:
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        raise SystemExit("OTEL_EXPORTER_OTLP_ENDPOINT is required (e.g. http://localhost:4318)")
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: SERVICE}))
    # With no explicit endpoint the exporter reads the environment variable
    # and appends /v1/traces itself.
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    return provider


async def list_tools(session: ClientSession, tracer: trace.Tracer) -> None:
    """List tools inside a span, with _meta, so discovery is part of the trace.

    Doing this before the first call also fills the SDK cache; otherwise
    call_tool would list tools by itself, without _meta (an orphan trace).
    """
    with tracer.start_as_current_span("tool.list", kind=trace.SpanKind.CLIENT):
        meta: dict[str, str] = {}
        propagate.inject(meta)
        params = PaginatedRequestParams(_meta=PaginatedRequestParams.Meta.model_validate(meta))
        listed = await session.list_tools(params=params)
        print("tools:", ", ".join(tool.name for tool in listed.tools))


async def call_tool(
    session: ClientSession, tracer: trace.Tracer, name: str, arguments: dict
) -> None:
    with tracer.start_as_current_span(f"tool.call {name}", kind=trace.SpanKind.CLIENT):
        meta: dict[str, str] = {}
        propagate.inject(meta)  # writes traceparent (and tracestate) into _meta
        result = await session.call_tool(name, arguments, meta=meta)
        status = "error" if result.isError else "ok"
        first = result.content[0] if result.content else None
        text = first.text if isinstance(first, TextContent) else ""
        print(f"{name}: {status} {result.structuredContent or text}")


async def run(url: str) -> str:
    tracer = trace.get_tracer(SERVICE)
    with tracer.start_as_current_span("agent.run") as root:
        trace_id = format(root.get_span_context().trace_id, "032x")
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await list_tools(session, tracer)
                await call_tool(session, tracer, "search_customers", {"query": "acme"})
                await call_tool(session, tracer, "get_ticket_info", {"ticket_id": "T-1001"})
                await call_tool(
                    session,
                    tracer,
                    "create_ticket",
                    {
                        "customer_id": "C-001",
                        "title": "Traced ticket",
                        "description": "Created by simulate_agent",
                    },
                )
    return trace_id


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--url", required=True, help="MCP endpoint, e.g. http://localhost:3000/mcp")
    args = parser.parse_args()

    provider = build_provider()
    try:
        trace_id = asyncio.run(run(args.url))
    finally:
        provider.shutdown()  # flush spans before the process exits
    print(f"trace_id={trace_id}", file=sys.stdout)


if __name__ == "__main__":
    main()
