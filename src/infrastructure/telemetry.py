"""OpenTelemetry tracing setup (OTLP over HTTP)."""

import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from config.settings import Settings

logger = logging.getLogger(__name__)

TRACES_PATH = "/v1/traces"


def traces_url(endpoint: str) -> str:
    """Build the OTLP/HTTP traces URL from a base endpoint such as http://host:4318.

    When the endpoint is passed in code (and not through the environment) the
    exporter uses it verbatim, so the signal path must be added here.
    """
    base = endpoint.rstrip("/")
    return base if base.endswith(TRACES_PATH) else f"{base}{TRACES_PATH}"


def setup_tracing(settings: Settings) -> TracerProvider | None:
    """Install a global TracerProvider that exports spans over OTLP/HTTP.

    Returns ``None`` (and leaves the no-op tracer in place) when tracing is
    disabled. Keep the returned provider and pass it to ``shutdown_tracing``.
    """
    if not settings.otel_enabled:
        logger.info("Tracing is disabled")
        return None
    if not settings.otel_exporter_otlp_endpoint:
        raise ValueError("OTEL_EXPORTER_OTLP_ENDPOINT is required to enable tracing")

    url = traces_url(settings.otel_exporter_otlp_endpoint)
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: settings.otel_service_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=url)))
    trace.set_tracer_provider(provider)
    logger.info("Tracing enabled (service=%s, exporter=%s)", settings.otel_service_name, url)
    return provider


def shutdown_tracing(provider: TracerProvider | None) -> None:
    """Flush pending spans and stop the exporter. Call it before the process exits."""
    if provider is None:
        return
    provider.shutdown()
    logger.info("Tracing shut down")
