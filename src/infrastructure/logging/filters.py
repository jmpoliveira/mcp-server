"""Logging filters."""

import logging
from collections.abc import Mapping
from typing import Any, Final

from opentelemetry import trace

from src.infrastructure.logging.record import extra_fields


class NonErrorFilter(logging.Filter):
    """Pass only DEBUG/INFO/WARNING records (stdout/stderr split)."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno < logging.ERROR


class TraceContextFilter(logging.Filter):
    """Copy the active trace and span ids onto the record.

    It must run on the thread that emits the log, before the record goes into
    the queue: the listener thread has no access to the caller's trace context.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        context = trace.get_current_span().get_span_context()
        if context.is_valid:
            record.trace_id = format(context.trace_id, "032x")
            record.span_id = format(context.span_id, "016x")
        else:
            record.trace_id = None
            record.span_id = None
        return True


REDACTED: Final = "***"
_MAX_DEPTH: Final = 5
_SENSITIVE_NAMES: Final = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "id_token",
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "set_cookie",
        "client_secret",
        "private_key",
    }
)
_SENSITIVE_SUFFIXES: Final = ("_password", "_secret", "_api_key", "_apikey", "_private_key")


def is_sensitive_key(key: str) -> bool:
    """True for names such as ``password``, ``Authorization`` or ``db_password``.

    Plural names such as ``max_tokens`` are deliberately not matched, so LLM
    token counts stay visible.
    """
    normalized = key.strip().lower().replace("-", "_")
    return normalized in _SENSITIVE_NAMES or normalized.endswith(_SENSITIVE_SUFFIXES)


def _redact(value: Any, depth: int = 0) -> Any:
    if depth >= _MAX_DEPTH:
        return value
    if isinstance(value, Mapping):
        return {
            key: REDACTED
            if isinstance(key, str) and is_sensitive_key(key)
            else _redact(item, depth + 1)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact(item, depth + 1) for item in value]
    return value


class RedactionFilter(logging.Filter):
    """Mask sensitive values passed through ``extra=...``.

    It does not inspect the message text: a secret interpolated into the
    message string cannot be detected reliably, so never log one.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in extra_fields(record.__dict__).items():
            if is_sensitive_key(key):
                setattr(record, key, REDACTED)
            elif isinstance(value, (Mapping, list, tuple)):
                setattr(record, key, _redact(value))
        return True
