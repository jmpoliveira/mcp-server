from src.interface.mcp.traced_server import TracedFastMCP


def indented_docstring_tool() -> str:
    return "ok"


# Set explicitly so the test does not depend on how this Python version compiles docstrings.
indented_docstring_tool.__doc__ = "First line,\n        second line.\n    "


async def test_tool_description_is_the_docstring_without_indentation():
    server = TracedFastMCP("test")

    server.add_tool(indented_docstring_tool)

    (tool,) = await server.list_tools()
    assert tool.description == "First line,\nsecond line."


async def test_explicit_tool_description_is_kept_as_given():
    server = TracedFastMCP("test")

    server.add_tool(indented_docstring_tool, description="  Given.  ")

    (tool,) = await server.list_tools()
    assert tool.description == "  Given.  "
