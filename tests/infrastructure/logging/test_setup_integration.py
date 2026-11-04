"""Runs real processes: logging is global state, so each scenario gets its own interpreter."""

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

SCRIPT = textwrap.dedent(
    """
    import logging
    from config.settings import get_settings
    from src.infrastructure.logging.setup import setup_logging, shutdown_logging
    from opentelemetry.sdk.trace import TracerProvider

    setup_logging(get_settings())
    log = logging.getLogger("scenario")
    tracer = TracerProvider().get_tracer("t")

    log.debug("debug message")
    with tracer.start_as_current_span("work"):
        log.info("inside span", extra={"ticket_id": "T-1", "password": "hunter2"})
    log.warning("warning message")
    try:
        1 / 0
    except ZeroDivisionError:
        log.exception("something failed")
    {tail}
    """
)


def run(tmp_path, tail="", expect_failure=False, **env):
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("LOG_", "APP_ENV", "OTEL_", "MCP_"))
    }
    environment.update(PYTHONPATH=str(PROJECT_ROOT), MCP_HOST="127.0.0.1", MCP_PORT="8000", **env)
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT.replace("{tail}", tail)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if not expect_failure:
        assert result.returncode == 0, result.stderr
    return result


def json_lines(text):
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def test_production_writes_only_json_to_stdout_and_stderr_and_no_file(tmp_path):
    result = run(tmp_path, APP_ENV="production")

    out, err = json_lines(result.stdout), json_lines(result.stderr)

    assert [r["message"] for r in out if r["logger"] == "scenario"] == [
        "inside span",
        "warning message",
    ]
    assert [r["level"] for r in err] == ["ERROR"]
    assert not (tmp_path / "logs").exists()


def test_production_hides_debug_and_shows_service_fields(tmp_path):
    result = run(
        tmp_path, APP_ENV="production", SERVICE_VERSION="3.1.4", OTEL_SERVICE_NAME="orders"
    )

    records = json_lines(result.stdout)

    assert "debug message" not in [r["message"] for r in records]
    assert all(
        (r["service"], r["env"], r["version"]) == ("orders", "production", "3.1.4") for r in records
    )


def test_trace_ids_exist_only_inside_the_span_and_secrets_are_redacted(tmp_path):
    records = {r["message"]: r for r in json_lines(run(tmp_path, APP_ENV="production").stdout)}

    inside, outside = records["inside span"], records["warning message"]

    assert len(inside["trace_id"]) == 32 and len(inside["span_id"]) == 16
    assert outside["trace_id"] is None
    assert inside["ticket_id"] == "T-1"
    assert inside["password"] == "***"


def test_exceptions_are_structured_in_the_error_stream(tmp_path):
    (record,) = json_lines(run(tmp_path, APP_ENV="production").stderr)

    assert record["message"] == "something failed"
    assert record["exc_type"] == "ZeroDivisionError"
    assert record["stacktrace"].endswith("ZeroDivisionError: division by zero")


def test_local_is_readable_on_the_terminal_and_json_in_the_file(tmp_path):
    result = run(tmp_path, APP_ENV="local")

    assert "debug message" in result.stdout
    assert not result.stdout.lstrip().startswith("{")

    file_records = json_lines((tmp_path / "logs" / "mcp-server.log.jsonl").read_text())
    messages = [r["message"] for r in file_records]
    assert {"debug message", "inside span", "warning message", "something failed"} <= set(messages)
    assert (
        next(r for r in file_records if r["message"] == "something failed")["exc_type"]
        == "ZeroDivisionError"
    )


def test_explicit_variables_override_the_profile(tmp_path):
    result = run(tmp_path, APP_ENV="production", LOG_LEVEL="WARNING", LOG_FORMAT="console")

    assert "inside span" not in result.stdout
    assert "warning message" in result.stdout
    assert not result.stdout.lstrip().startswith("{")


def test_records_logged_just_before_exit_are_flushed(tmp_path):
    result = run(tmp_path, tail='log.warning("last words")', APP_ENV="production")

    assert "last words" in [r["message"] for r in json_lines(result.stdout)]


def test_configuring_twice_does_not_duplicate_output(tmp_path):
    tail = "setup_logging(get_settings())\nlog.warning('once')"
    result = run(tmp_path, tail=tail, APP_ENV="production")

    assert [r["message"] for r in json_lines(result.stdout)].count("once") == 1


def test_the_packaged_template_is_found_through_importlib_resources():
    from importlib import resources

    assert resources.files("config").joinpath("logging.json").is_file()


def test_an_unwritable_log_file_fails_at_startup_with_a_clear_message(tmp_path):
    blocker = tmp_path / "not_a_directory"
    blocker.write_text("x")

    result = run(
        tmp_path, expect_failure=True, APP_ENV="local", LOG_FILE=str(blocker / "app.jsonl")
    )

    assert result.returncode != 0
    assert "Could not configure logging" in result.stderr
