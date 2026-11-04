from unittest.mock import MagicMock, patch

from config.settings import Settings
from src.interface.mcp import runner


def test_run_http_uses_our_logging_pipeline_and_the_configured_address():
    settings = Settings(_env_file=None, mcp_host="127.0.0.1", mcp_port=3000)
    server = MagicMock()

    with (
        patch.object(runner.uvicorn, "Config") as config,
        patch.object(runner.uvicorn, "Server") as uvicorn_server,
    ):
        runner.run_http(server, settings)

    config.assert_called_once_with(
        server.streamable_http_app.return_value, host="127.0.0.1", port=3000, log_config=None
    )
    uvicorn_server.return_value.run.assert_called_once_with()
