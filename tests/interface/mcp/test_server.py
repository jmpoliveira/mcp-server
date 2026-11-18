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


async def test_server_exposes_exactly_the_four_tools(server):
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        listed = await client.list_tools()

    assert {tool.name for tool in listed.tools} == {
        "search_customers",
        "get_ticket_info",
        "search_tickets",
        "create_ticket",
    }


async def test_read_tools_are_annotated_read_only(server):
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        listed = await client.list_tools()

    hints = {tool.name: tool.annotations.readOnlyHint for tool in listed.tools}
    assert hints == {
        "search_customers": True,
        "get_ticket_info": True,
        "search_tickets": True,
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


async def test_search_tickets_is_listed_with_its_contract(server):
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        listed = await client.list_tools()

    (tool,) = [tool for tool in listed.tools if tool.name == "search_tickets"]
    properties = tool.inputSchema["properties"]
    assert tool.description is not None
    assert tool.description.startswith("List a customer's support tickets, newest first")
    assert "An empty list means the customer exists" in tool.description
    assert tool.inputSchema["required"] == ["customer_id"]
    assert set(properties) == {"customer_id", "status", "max_results"}
    assert properties["max_results"]["default"] == 10
    assert properties["status"]["default"] is None
    assert tool.annotations is not None
    assert tool.annotations.openWorldHint is False


async def test_search_tickets_returns_count_and_tickets(server):
    result = await call(server, "search_tickets", {"customer_id": "C-002"})

    assert result.isError is False
    assert result.structuredContent["count"] == 1
    assert result.structuredContent["tickets"][0]["id"] == "T-1002"


async def test_search_tickets_for_a_customer_without_tickets_is_an_empty_list(server):
    result = await call(server, "search_tickets", {"customer_id": "C-004"})

    assert result.isError is False
    assert result.structuredContent == {"count": 0, "tickets": []}


async def test_search_tickets_includes_tickets_created_at_runtime_newest_first(server):
    await call(
        server,
        "create_ticket",
        {"customer_id": "C-001", "title": "New", "description": "Details"},
    )

    result = await call(server, "search_tickets", {"customer_id": "C-001", "status": "open"})

    assert [ticket["id"] for ticket in result.structuredContent["tickets"]] == ["T-1004"]


async def test_search_tickets_for_an_unknown_customer_is_a_tool_error(server):
    result = await call(server, "search_tickets", {"customer_id": "C-404"})

    assert result.isError is True
    assert "Customer C-404 not found" in result.content[0].text


async def test_search_tickets_rejects_an_unknown_status_through_the_schema(server):
    result = await call(server, "search_tickets", {"customer_id": "C-001", "status": "pending"})

    assert result.isError is True
