import json
import logging
import sys

from src.infrastructure.logging.formatters import ConsoleFormatter, JsonFormatter

STATIC = {"service": "svc", "env": "test", "version": "1.2.3"}


class CustomError(Exception):
    pass


def make_record(msg="hello", level=logging.INFO, exc_info=None, **extra):
    record = logging.LogRecord("my.logger", level, __file__, 42, msg, None, exc_info)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def raised(exc):
    try:
        raise exc
    except type(exc):
        return sys.exc_info()


def format_json(record, **kwargs):
    return json.loads(JsonFormatter(static_fields=STATIC, **kwargs).format(record))


def test_json_contains_the_core_fields_in_a_stable_order():
    data = format_json(make_record())

    assert list(data)[:11] == [
        "timestamp",
        "level",
        "message",
        "logger",
        "service",
        "env",
        "version",
        "trace_id",
        "span_id",
        "module",
        "function",
    ]
    assert (data["level"], data["message"], data["logger"], data["line"]) == (
        "INFO",
        "hello",
        "my.logger",
        42,
    )
    assert (data["service"], data["env"], data["version"]) == ("svc", "test", "1.2.3")


def test_json_timestamp_is_utc_iso_with_milliseconds():
    data = format_json(make_record())

    assert data["timestamp"].endswith("+00:00")
    assert len(data["timestamp"].split(".")[1]) == len("123+00:00")


def test_json_trace_ids_are_null_without_a_span_and_present_with_one():
    assert format_json(make_record())["trace_id"] is None

    data = format_json(make_record(trace_id="a" * 32, span_id="b" * 16))

    assert (data["trace_id"], data["span_id"]) == ("a" * 32, "b" * 16)


def test_json_includes_extras_without_overwriting_core_fields():
    record = make_record(ticket_id="T-1", service="spoofed")
    record.level = "spoofed"  # an extra named like a core JSON field
    data = format_json(record)

    assert data["ticket_id"] == "T-1"
    assert (data["level"], data["service"]) == ("INFO", "svc")


def test_json_handles_values_that_are_not_serializable():
    data = format_json(make_record(payload=object()))

    assert data["payload"].startswith("<object object")


def test_json_exception_fields_and_single_line():
    record = make_record(level=logging.ERROR, exc_info=raised(ValueError("bad value")))
    line = JsonFormatter(static_fields=STATIC).format(record)
    data = json.loads(line)

    assert "\n" not in line
    assert data["exc_type"] == "ValueError"
    assert data["exc_message"] == "bad value"
    assert data["stacktrace"].startswith("Traceback")
    assert data["stacktrace"].endswith("ValueError: bad value")


def test_json_exception_type_is_module_qualified_for_custom_errors():
    data = format_json(make_record(exc_info=raised(CustomError("x"))))

    assert data["exc_type"].endswith(".CustomError")


def test_json_has_no_exception_fields_without_an_exception():
    data = format_json(make_record())

    assert not {"exc_type", "exc_message", "stacktrace"} & data.keys()


def test_json_message_is_truncated_keeping_the_beginning():
    data = format_json(make_record(msg="x" * 500), max_message_chars=200)

    assert data["message"].startswith("x" * 200)
    assert data["message"].endswith("[truncated]")


def test_json_stacktrace_is_truncated_keeping_the_end():
    exc = raised(ValueError("y" * 5000 + " final reason"))
    data = format_json(make_record(exc_info=exc), max_stacktrace_chars=300)

    assert data["stacktrace"].startswith("...[truncated]")
    assert "final reason" in data["stacktrace"]
    assert len(data["stacktrace"]) < 400


def test_console_line_is_readable_and_shows_a_short_trace_id():
    line = ConsoleFormatter().format(make_record(trace_id="1a2b3c4d" + "0" * 24))

    assert "INFO" in line and "my.logger: [1a2b3c4d] hello" in line


def test_console_line_has_no_trace_prefix_without_a_span():
    line = ConsoleFormatter().format(make_record())

    assert line.endswith("my.logger: hello")


def test_console_appends_the_traceback():
    line = ConsoleFormatter().format(make_record(exc_info=raised(ValueError("bad"))))

    assert "Traceback" in line and "ValueError: bad" in line


def test_console_formatter_does_not_modify_the_record():
    record = make_record()

    ConsoleFormatter().format(record)

    assert not hasattr(record, "trace_prefix")
