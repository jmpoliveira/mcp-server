"""Helpers to read a LogRecord."""

from typing import Any, Final

# Attributes that exist on every LogRecord, plus the ones set by our own filters.
# Everything else on a record was added through ``extra=...``.
RESERVED_ATTRS: Final[frozenset[str]] = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
        "trace_id",
        "span_id",
        "trace_prefix",
    }
)


def extra_fields(record_dict: dict[str, Any]) -> dict[str, Any]:
    """Return the custom fields a caller added with ``extra=...``."""
    return {k: v for k, v in record_dict.items() if k not in RESERVED_ATTRS}
