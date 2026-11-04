"""Logging handlers."""

import copy
import logging
import queue
from logging.handlers import QueueHandler, RotatingFileHandler
from pathlib import Path
from typing import Any


class SafeRotatingFileHandler(RotatingFileHandler):
    """Rotating file handler that creates the parent directory first."""

    def __init__(self, filename: str, *args: Any, **kwargs: Any) -> None:
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        super().__init__(filename, *args, **kwargs)


class StructuredQueueHandler(QueueHandler):
    """QueueHandler for non-blocking logging with a bounded queue.

    - ``prepare`` keeps ``exc_info`` and ``stack_info``. The stock
      implementation flattens the traceback into the message and clears
      ``exc_info``, so the JSON formatter could never emit structured
      exception fields.
    - ``enqueue`` never blocks and never raises: when the queue is full the
      record is dropped and counted in ``dropped``, so a log storm cannot
      stall the application or exhaust memory.
    """

    def __init__(self, queue: "queue.Queue[logging.LogRecord]") -> None:
        super().__init__(queue)
        self.dropped = 0

    def prepare(self, record: logging.LogRecord) -> logging.LogRecord:
        record = copy.copy(record)  # do not affect other handlers
        record.message = record.getMessage()
        return record

    def enqueue(self, record: logging.LogRecord) -> None:
        try:
            self.queue.put_nowait(record)
        except queue.Full:
            self.dropped += 1
