import signal

import pytest

import main


def test_sigterm_handler_raises_a_clean_system_exit():
    with pytest.raises(SystemExit) as exit_info:
        main.exit_on_sigterm(signal.SIGTERM, None)

    assert exit_info.value.code == 0


def test_ctrl_c_is_a_clean_shutdown_that_still_flushes(monkeypatch):
    from unittest.mock import MagicMock

    shutdown_tracing, shutdown_logging = MagicMock(), MagicMock()
    monkeypatch.setenv("MCP_HOST", "127.0.0.1")
    monkeypatch.setenv("MCP_PORT", "8000")
    monkeypatch.setattr(main.signal, "signal", MagicMock())
    monkeypatch.setattr(main, "setup_logging", MagicMock())
    monkeypatch.setattr(main, "setup_tracing", MagicMock())
    monkeypatch.setattr(main, "run_http", MagicMock(side_effect=KeyboardInterrupt))
    monkeypatch.setattr(main, "shutdown_tracing", shutdown_tracing)
    monkeypatch.setattr(main, "shutdown_logging", shutdown_logging)

    main.main()  # must not raise

    shutdown_tracing.assert_called_once()
    shutdown_logging.assert_called_once()
