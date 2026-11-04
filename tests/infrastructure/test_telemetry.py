from unittest.mock import MagicMock, patch

import pytest

from config.settings import Settings
from src.infrastructure import telemetry


def make_settings(**overrides):
    values = {"mcp_host": "127.0.0.1", "mcp_port": 8000, **overrides}
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize(
    ("endpoint", "expected"),
    [
        ("http://jaeger:4318", "http://jaeger:4318/v1/traces"),
        ("http://jaeger:4318/", "http://jaeger:4318/v1/traces"),
        ("http://jaeger:4318/v1/traces", "http://jaeger:4318/v1/traces"),
    ],
)
def test_traces_url_appends_the_signal_path_once(endpoint, expected):
    assert telemetry.traces_url(endpoint) == expected


def test_setup_does_nothing_when_tracing_is_disabled():
    with patch.object(telemetry, "OTLPSpanExporter") as exporter:
        assert telemetry.setup_tracing(make_settings()) is None

    exporter.assert_not_called()


def test_setup_configures_exporter_service_name_and_global_provider():
    settings = make_settings(
        otel_enabled=True,
        otel_service_name="my-service",
        otel_exporter_otlp_endpoint="http://jaeger:4318",
    )

    with (
        patch.object(telemetry, "OTLPSpanExporter") as exporter,
        patch.object(telemetry.trace, "set_tracer_provider") as set_provider,
    ):
        provider = telemetry.setup_tracing(settings)

    exporter.assert_called_once_with(endpoint="http://jaeger:4318/v1/traces")
    set_provider.assert_called_once_with(provider)
    assert provider.resource.attributes["service.name"] == "my-service"
    provider.shutdown()


def test_shutdown_flushes_the_provider():
    provider = MagicMock()

    telemetry.shutdown_tracing(provider)

    provider.shutdown.assert_called_once_with()


def test_shutdown_accepts_none():
    telemetry.shutdown_tracing(None)
