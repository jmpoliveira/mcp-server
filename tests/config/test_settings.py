import pytest
from pydantic import ValidationError

from config.settings import Settings

_ENV_VARS = (
    "MCP_HOST",
    "MCP_PORT",
    "APP_ENV",
    "SERVICE_VERSION",
    "OTEL_ENABLED",
    "OTEL_SERVICE_NAME",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "LOG_LEVEL",
    "LOG_FORMAT",
    "LOG_FILE_ENABLED",
    "LOG_FILE",
    "LOG_ACCESS",
    "LOG_MAX_MESSAGE_CHARS",
    "LOG_MAX_STACKTRACE_CHARS",
    "LOG_QUEUE_SIZE",
)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in _ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def make(**overrides):
    values = {"mcp_host": "127.0.0.1", "mcp_port": 9000, **overrides}
    return Settings(_env_file=None, **values)


def test_loads_values_from_environment(monkeypatch):
    monkeypatch.setenv("MCP_HOST", "127.0.0.1")
    monkeypatch.setenv("MCP_PORT", "9000")

    settings = Settings(_env_file=None)

    assert (settings.mcp_host, settings.mcp_port) == ("127.0.0.1", 9000)


def test_fails_fast_when_host_and_port_are_missing():
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


# ---------------------------------------------------------------- tracing
def test_tracing_is_disabled_by_default():
    assert make().otel_enabled is False


def test_enabled_tracing_requires_an_endpoint():
    with pytest.raises(ValidationError, match="OTEL_EXPORTER_OTLP_ENDPOINT"):
        make(otel_enabled=True)


def test_enabled_tracing_accepts_an_endpoint():
    settings = make(otel_enabled=True, otel_exporter_otlp_endpoint="http://jaeger:4318")

    assert settings.otel_exporter_otlp_endpoint == "http://jaeger:4318"


# ---------------------------------------------------------------- logging profiles
def test_default_environment_is_production():
    assert make().app_env == "production"


@pytest.mark.parametrize(
    ("env", "level", "fmt", "file_enabled"),
    [
        ("local", "DEBUG", "console", True),
        ("development", "DEBUG", "json", False),
        ("production", "INFO", "json", False),
    ],
)
def test_each_environment_has_its_logging_defaults(env, level, fmt, file_enabled):
    options = make(app_env=env).logging_options

    assert (options.level, options.format, options.file_enabled) == (level, fmt, file_enabled)


def test_explicit_values_override_the_environment_profile():
    options = make(
        app_env="production",
        log_level="debug",
        log_format="console",
        log_file_enabled=True,
    ).logging_options

    assert (options.level, options.format, options.file_enabled) == ("DEBUG", "console", True)


def test_explicit_false_disables_the_file_even_in_local():
    assert make(app_env="local", log_file_enabled=False).logging_options.file_enabled is False


def test_log_settings_are_read_from_environment_variables(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("LOG_LEVEL", "warning")
    monkeypatch.setenv("LOG_FORMAT", "json")

    options = make().logging_options

    assert (options.level, options.format) == ("WARNING", "json")


def test_service_identity_matches_the_trace_identity():
    options = make(
        otel_service_name="orders", app_env="development", service_version="2.3.4"
    ).logging_options

    assert (options.service, options.environment, options.version) == (
        "orders",
        "development",
        "2.3.4",
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"log_level": "verbose"},
        {"log_format": "xml"},
        {"app_env": "staging"},
        {"log_max_message_chars": 10},
        {"log_max_stacktrace_chars": 99999},
        {"log_queue_size": 1},
    ],
)
def test_invalid_logging_settings_are_rejected(overrides):
    with pytest.raises(ValidationError):
        make(**overrides)


def test_empty_variables_are_treated_as_not_set(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "")
    monkeypatch.setenv("LOG_FORMAT", "")
    monkeypatch.setenv("LOG_FILE_ENABLED", "")

    options = make(app_env="production").logging_options

    assert (options.level, options.format, options.file_enabled) == ("INFO", "json", False)


def test_an_empty_required_variable_is_still_an_error(monkeypatch):
    monkeypatch.setenv("MCP_HOST", "")
    monkeypatch.setenv("MCP_PORT", "9000")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
