import logging

import pytest
from opentelemetry.sdk.trace import TracerProvider

from src.infrastructure.logging.filters import (
    REDACTED,
    NonErrorFilter,
    RedactionFilter,
    TraceContextFilter,
    is_sensitive_key,
)


def make_record(**extra):
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "msg", None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


@pytest.mark.parametrize(
    ("level", "expected"),
    [
        (logging.DEBUG, True),
        (logging.WARNING, True),
        (logging.ERROR, False),
        (logging.CRITICAL, False),
    ],
)
def test_non_error_filter_passes_only_records_below_error(level, expected):
    record = make_record()
    record.levelno = level

    assert NonErrorFilter().filter(record) is expected


def test_trace_filter_sets_null_ids_outside_a_span():
    record = make_record()

    assert TraceContextFilter().filter(record) is True

    assert (record.trace_id, record.span_id) == (None, None)


def test_trace_filter_copies_the_active_ids():
    tracer = TracerProvider().get_tracer("test")
    record = make_record()

    with tracer.start_as_current_span("work") as span:
        TraceContextFilter().filter(record)
        expected = span.get_span_context()

    assert record.trace_id == format(expected.trace_id, "032x")
    assert record.span_id == format(expected.span_id, "016x")


@pytest.mark.parametrize(
    "key",
    ["password", "Authorization", "api-key", "API_KEY", "db_password", "client_secret", "token"],
)
def test_sensitive_keys_are_detected(key):
    assert is_sensitive_key(key) is True


@pytest.mark.parametrize("key", ["ticket_id", "max_tokens", "prompt_tokens", "customer_id", "tool"])
def test_ordinary_keys_are_not_sensitive(key):
    assert is_sensitive_key(key) is False


def test_redaction_masks_sensitive_extras_and_keeps_the_rest():
    record = make_record(password="hunter2", ticket_id="T-1", max_tokens=256)

    RedactionFilter().filter(record)

    assert (record.password, record.ticket_id, record.max_tokens) == (REDACTED, "T-1", 256)


def test_redaction_masks_nested_values():
    record = make_record(
        headers={"Authorization": "Bearer abc", "accept": "json"},
        items=[{"api_key": "k"}, {"name": "n"}],
    )

    RedactionFilter().filter(record)

    assert record.headers == {"Authorization": REDACTED, "accept": "json"}
    assert record.items == [{"api_key": REDACTED}, {"name": "n"}]


def test_redaction_does_not_touch_the_message():
    record = make_record(password="x")
    record.msg = "password=hunter2"

    RedactionFilter().filter(record)

    assert record.getMessage() == "password=hunter2"  # documented limitation
