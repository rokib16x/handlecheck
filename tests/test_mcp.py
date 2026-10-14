"""Starts the real MCP server over stdio and calls it with the official client."""
import asyncio
import sys

import pytest

pytest.importorskip("mcp")


async def _run():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command=sys.executable, args=["-m", "handlecheck.mcp_server"])
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        names = {t.name for t in tools.tools}
        # "bad name" is rejected before any network access, so this stays offline
        res = await session.call_tool("check_username", {"username": "bad name"})
        return names, res


def test_mcp_tools_over_stdio():
    names, res = asyncio.run(asyncio.wait_for(_run(), 60))
    assert names == {"check_username", "check_usernames", "list_platforms"}
    assert not getattr(res, "is_error", getattr(res, "isError", False))
    assert "INVALID" in str(res.content)
