"""Keeps examples/ honest: every request is replayed over HTTP and compared
with its stored response."""

import json
import re
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from config.settings import Settings
from src.interface.mcp.server import build_server

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
REQUESTS = sorted((EXAMPLES / "requests").glob("*.json"))

# Values that legitimately change between runs or dependency versions.
VOLATILE = [
    (re.compile(r"\d{4}-\d{2}-\d{2}T[\d:.]+\+00:00"), "<timestamp>"),
    (re.compile(r"errors\.pydantic\.dev/[\d.]+/"), "errors.pydantic.dev/<version>/"),
]


def normalize(payload: dict) -> str:
    text = json.dumps(payload, sort_keys=True)
    for pattern, replacement in VOLATILE:
        text = pattern.sub(replacement, text)
    return text


def parse_sse(body: str) -> dict:
    """The server answers with Server-Sent Events: keep the JSON-RPC payload."""
    data = next(line[len("data: ") :] for line in body.splitlines() if line.startswith("data: "))
    return json.loads(data)


@pytest.fixture
def client(use_cases):
    settings = Settings(_env_file=None, mcp_host="127.0.0.1", mcp_port=8000)
    app = build_server(settings, *use_cases).streamable_http_app()
    # The base URL host must be allowed by the server's DNS rebinding protection.
    with TestClient(app, base_url="http://127.0.0.1:8000") as test_client:
        yield test_client


def test_every_request_has_a_response_and_vice_versa():
    requests = {path.name for path in (EXAMPLES / "requests").glob("*.json")}
    responses = {path.name for path in (EXAMPLES / "responses").glob("*.json")}

    assert requests == responses
    assert requests, "examples/requests must not be empty"


@pytest.mark.parametrize("request_file", REQUESTS, ids=lambda path: path.stem)
def test_request_produces_the_stored_response(client, request_file):
    response = client.post(
        "/mcp",
        content=request_file.read_bytes(),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )

    expected = json.loads((EXAMPLES / "responses" / request_file.name).read_text())
    assert response.status_code == 200
    assert normalize(parse_sse(response.text)) == normalize(expected)
