"""Logging setup: dictConfig template + environment settings + a queue listener."""

import atexit
import copy
import json
import logging
import logging.config
import logging.handlers
from importlib import resources
from typing import Any

from config.settings import Settings
from src.infrastructure.logging.handlers import StructuredQueueHandler

logger = logging.getLogger(__name__)

_QUEUE_HANDLER = "queue_handler"
_listener: logging.handlers.QueueListener | None = None


def _load_template() -> dict[str, Any]:
    text = resources.files("config").joinpath("logging.json").read_text(encoding="utf-8")
    return json.loads(text)


def build_config(settings: Settings) -> dict[str, Any]:
    """Return the dictConfig dict: the static template plus the resolved settings.

    Pure function, no global state touched, so it is easy to test.
    """
    options = settings.logging_options
    config = copy.deepcopy(_load_template())

    config["root"]["level"] = options.level
    for name in ("stdout", "stderr"):
        config["handlers"][name]["formatter"] = options.format

    config["formatters"]["json"].update(
        static_fields={
            "service": options.service,
            "env": options.environment,
            "version": options.version,
        },
        max_message_chars=options.max_message_chars,
        max_stacktrace_chars=options.max_stacktrace_chars,
    )

    queue_handler = config["handlers"][_QUEUE_HANDLER]
    queue_handler["queue"]["maxsize"] = options.queue_size
    if options.file_enabled:
        config["handlers"]["file_all"]["filename"] = str(options.file_path)
    else:
        config["handlers"].pop("file_all")
        queue_handler["handlers"].remove("file_all")

    config["loggers"]["uvicorn.access"]["level"] = "INFO" if options.access_log else "WARNING"
    return config


def setup_logging(settings: Settings) -> None:
    """Configure logging once. Call it before creating the FastMCP server.

    FastMCP configures logging by itself when it is created, but only if the
    root logger has no handlers yet.
    """
    global _listener
    if _listener is not None:
        return  # already configured

    try:
        logging.config.dictConfig(build_config(settings))
    except ValueError as err:
        # dictConfig wraps the real cause, e.g. a log file that cannot be created.
        raise RuntimeError(f"Could not configure logging: {err.__cause__ or err}") from err
    handler = logging.getHandlerByName(_QUEUE_HANDLER)
    if not isinstance(handler, StructuredQueueHandler):
        raise RuntimeError(
            "logging.json must define a StructuredQueueHandler named 'queue_handler'"
        )

    if handler.listener is None:
        raise RuntimeError("The queue handler has no listener to start")
    _listener = handler.listener
    _listener.start()
    atexit.register(shutdown_logging)

    options = settings.logging_options
    logger.info(
        "Logging configured (env=%s, level=%s, format=%s, file=%s)",
        options.environment,
        options.level,
        options.format,
        options.file_path if options.file_enabled else "off",
    )


def shutdown_logging() -> None:
    """Flush the queue, stop the listener and detach the queue handler. Idempotent."""
    global _listener
    if _listener is None:
        return
    handler = logging.getHandlerByName(_QUEUE_HANDLER)
    if isinstance(handler, StructuredQueueHandler) and handler.dropped:
        logger.warning("Dropped %d log records because the queue was full", handler.dropped)

    _listener.stop()  # processes everything already queued
    _listener = None
    if handler is not None:
        logging.getLogger().removeHandler(handler)  # later records go to logging.lastResort
