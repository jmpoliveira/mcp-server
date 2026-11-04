"""Log formatters: JSON lines for machines, a short readable line for developers."""

import copy
import json
import logging
from datetime import UTC, datetime
from typing import Any

from src.infrastructure.logging.record import extra_fields

_TRUNCATED = "...[truncated]"


def _truncate_head(text: str, limit: int) -> str:
    """Keep the beginning (messages)."""
    return text if len(text) <= limit else text[:limit] + _TRUNCATED


def _truncate_tail(text: str, limit: int) -> str:
    """Keep the end (tracebacks end with the exception type and message)."""
    return text if len(text) <= limit else _TRUNCATED + text[-limit:]


def _qualified_name(exc_type: type[BaseException]) -> str:
    if exc_type.__module__ == "builtins":
        return exc_type.__qualname__
    return f"{exc_type.__module__}.{exc_type.__qualname__}"


class JsonFormatter(logging.Formatter):
    """One JSON object per line (JSONL) with a stable schema.

    Fields: timestamp (UTC), level, message, logger, the static service fields
    (service, env, version), trace_id, span_id, module, function, line, then
    caller extras, then exc_type / exc_message / stacktrace for exceptions.

    Message and stacktrace are capped so a line stays well below the 16 KiB
    at which Docker splits log lines.
    """

    def __init__(
        self,
        *,
        static_fields: dict[str, str] | None = None,
        max_message_chars: int = 4000,
        max_stacktrace_chars: int = 6000,
    ) -> None:
        super().__init__()
        self._static_fields = dict(static_fields or {})
        self._max_message = max_message_chars
        self._max_stacktrace = max_stacktrace_chars

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "message": _truncate_head(record.getMessage(), self._max_message),
            "logger": record.name,
            **self._static_fields,
            "trace_id": getattr(record, "trace_id", None),
            "span_id": getattr(record, "span_id", None),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        for key, value in extra_fields(record.__dict__).items():
            payload.setdefault(key, value)  # extras never overwrite core fields

        if record.exc_info and record.exc_info[0] is not None:
            exc_type, exc_value, _ = record.exc_info
            payload["exc_type"] = _qualified_name(exc_type)
            payload["exc_message"] = _truncate_head(str(exc_value), self._max_message)
            payload["stacktrace"] = _truncate_tail(
                self.formatException(record.exc_info), self._max_stacktrace
            )
        if record.stack_info:
            payload["stack_info"] = _truncate_tail(record.stack_info, self._max_stacktrace)

        return json.dumps(payload, ensure_ascii=False, default=str)


class ConsoleFormatter(logging.Formatter):
    """Short human-readable line: ``10:00:01 INFO     logger: [1a2b3c4d] message``.

    The bracketed value is the first 8 characters of the trace id; the full ids
    are in the JSON output.
    """

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s %(levelname)-8s %(name)s: %(trace_prefix)s%(message)s",
            datefmt="%H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        view = copy.copy(record)  # do not leak the extra attribute to other handlers
        trace_id = getattr(record, "trace_id", None)
        view.trace_prefix = f"[{trace_id[:8]}] " if trace_id else ""
        return super().format(view)
