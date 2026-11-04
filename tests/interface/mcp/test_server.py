"""Tests the real MCP server in memory, without opening network ports."""

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from config.settings import Settings
from src.interface.mcp.server import build_server


@pytest.fixture
def server(use_cases):
    settings = Settings(_env_file=None, mcp_host="127.0.0.1", mcp_port=8000)
    return build_server(settings, *use_cases)


async def call(server, name, arguments):
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        return await client.call_tool(name, arguments)


async def test_server_exposes_exactly_the_three_tools(server):
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        listed = await client.list_tools()

    assert {tool.name for tool in listed.tools} == {
        "search_customers",
        "get_ticket_info",
        "create_ticket",
    }


async def test_read_tools_are_annotated_read_only(server):
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        listed = await client.list_tools()

    hints = {tool.name: tool.annotations.readOnlyHint for tool in listed.tools}
    assert hints == {
        "search_customers": True,
        "get_ticket_info": True,
        "create_ticket": False,
    }


async def test_search_customers_returns_structured_data(server):
    result = await call(server, "search_customers", {"query": "globex"})

    assert result.isError is False
    assert result.structuredContent["count"] == 1
    assert result.structuredContent["customers"][0]["id"] == "C-002"


async def test_get_ticket_info_returns_ticket(server):
    result = await call(server, "get_ticket_info", {"ticket_id": "T-1003"})

    assert result.structuredContent["status"] == "resolved"


async def test_create_ticket_then_read_it_back(server):
    created = await call(
        server,
        "create_ticket",
        {"customer_id": "C-001", "title": "New", "description": "Details"},
    )
    new_id = created.structuredContent["id"]

    fetched = await call(server, "get_ticket_info", {"ticket_id": new_id})

    assert (new_id, fetched.structuredContent["title"]) == ("T-1004", "New")


async def test_domain_errors_become_tool_errors_with_a_clear_message(server):
    result = await call(server, "get_ticket_info", {"ticket_id": "T-9999"})

    assert result.isError is True
    assert "T-9999 not found" in result.content[0].text


async def test_invalid_priority_is_rejected_by_the_schema(server):
    result = await call(
        server,
        "create_ticket",
        {"customer_id": "C-001", "title": "x", "description": "y", "priority": "critical"},
    )

    assert result.isError is True
