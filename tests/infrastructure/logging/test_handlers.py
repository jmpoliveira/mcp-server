import logging
import queue

from src.infrastructure.logging.handlers import (
    SafeRotatingFileHandler,
    StructuredQueueHandler,
)


def make_record(exc_info=None):
    return logging.LogRecord("t", logging.ERROR, __file__, 1, "boom %s", ("now",), exc_info)


def raised():
    import sys

    try:
        _ = 1 / 0
    except ZeroDivisionError:
        return sys.exc_info()


def test_prepare_keeps_exc_info_and_resolves_the_message():
    handler = StructuredQueueHandler(queue.Queue())
    original = make_record(raised())

    prepared = handler.prepare(original)

    assert prepared.exc_info is original.exc_info
    assert prepared.message == "boom now"


def test_prepare_does_not_modify_the_original_record():
    handler = StructuredQueueHandler(queue.Queue())
    original = make_record()

    handler.prepare(original)

    assert not hasattr(original, "message")


def test_handle_puts_the_record_in_the_queue():
    q = queue.Queue()
    handler = StructuredQueueHandler(q)

    handler.handle(make_record())

    assert q.qsize() == 1


def test_full_queue_drops_records_without_blocking_or_raising():
    q = queue.Queue(maxsize=1)
    handler = StructuredQueueHandler(q)

    for _ in range(4):
        handler.handle(make_record())

    assert q.qsize() == 1
    assert handler.dropped == 3


def test_file_handler_creates_missing_parent_directories(tmp_path):
    target = tmp_path / "a" / "b" / "app.log.jsonl"

    handler = SafeRotatingFileHandler(str(target), delay=True)
    handler.close()

    assert target.parent.is_dir()
