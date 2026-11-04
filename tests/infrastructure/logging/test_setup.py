"""build_config is a pure function: no global logging state is touched."""

import pytest

from config.settings import Settings
from src.infrastructure.logging.setup import build_config


def make(**overrides):
    values = {"mcp_host": "127.0.0.1", "mcp_port": 8000, **overrides}
    return Settings(_env_file=None, **values)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in ("APP_ENV", "LOG_LEVEL", "LOG_FORMAT", "LOG_FILE_ENABLED", "LOG_ACCESS"):
        monkeypatch.delenv(name, raising=False)


def test_production_config_is_json_on_stdout_without_a_file():
    config = build_config(make(app_env="production"))

    assert config["root"]["level"] == "INFO"
    assert config["handlers"]["stdout"]["formatter"] == "json"
    assert config["handlers"]["stderr"]["formatter"] == "json"
    assert "file_all" not in config["handlers"]
    assert "file_all" not in config["handlers"]["queue_handler"]["handlers"]


def test_local_config_is_console_plus_a_file():
    config = build_config(make(app_env="local", log_file="custom/app.jsonl"))

    assert config["root"]["level"] == "DEBUG"
    assert config["handlers"]["stdout"]["formatter"] == "console"
    assert config["handlers"]["file_all"]["filename"] == "custom/app.jsonl"
    assert "file_all" in config["handlers"]["queue_handler"]["handlers"]


def test_file_handler_always_writes_json_regardless_of_the_terminal_format():
    config = build_config(make(app_env="local"))

    assert config["handlers"]["file_all"]["formatter"] == "json"


def test_json_formatter_receives_the_service_identity_and_limits():
    config = build_config(
        make(
            otel_service_name="orders",
            app_env="development",
            service_version="9.9.9",
            log_max_message_chars=500,
            log_max_stacktrace_chars=700,
        )
    )

    formatter = config["formatters"]["json"]
    assert formatter["static_fields"] == {
        "service": "orders",
        "env": "development",
        "version": "9.9.9",
    }
    assert (formatter["max_message_chars"], formatter["max_stacktrace_chars"]) == (500, 700)


def test_queue_size_comes_from_settings():
    config = build_config(make(log_queue_size=250))

    assert config["handlers"]["queue_handler"]["queue"]["maxsize"] == 250


@pytest.mark.parametrize(("access", "level"), [(False, "WARNING"), (True, "INFO")])
def test_uvicorn_access_log_is_opt_in(access, level):
    config = build_config(make(log_access=access))

    assert config["loggers"]["uvicorn.access"]["level"] == level


def test_noisy_third_party_loggers_are_quiet_even_in_debug():
    config = build_config(make(log_level="DEBUG"))

    assert {
        name: config["loggers"][name]["level"]
        for name in ("urllib3", "httpx", "httpcore", "asyncio", "sse_starlette")
    } == dict.fromkeys(("urllib3", "httpx", "httpcore", "asyncio", "sse_starlette"), "WARNING")


def test_the_template_is_not_mutated_between_calls():
    build_config(make(app_env="local"))

    config = build_config(make(app_env="production"))

    assert config["handlers"]["stdout"]["formatter"] == "json"
    assert build_config(make(app_env="local"))["handlers"]["file_all"]["filename"]
