"""MCP server exposing handlecheck as tools for Claude Desktop, Claude Code, Cursor, etc.

Run with:  handlecheck-mcp          (stdio transport)
Needs the optional extra:  pip install "handlecheck[mcp]"
"""
from __future__ import annotations

from dataclasses import asdict

from .checkers import PLATFORMS, check_all

try:  # mcp >= 2
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # mcp 1.x
    try:
        from mcp.server.fastmcp import FastMCP as _Server
    except ImportError as e:  # pragma: no cover
        raise SystemExit(
            'The MCP server needs the "mcp" package: pip install "handlecheck[mcp]"'
        ) from e

mcp = _Server(
    "handlecheck",
    instructions=(
        "Check whether a username exists on social platforms without logging in. "
        "UNKNOWN means the check could not tell (rate limit or site change), not 'absent'."
    ),
)


def _rows(username: str, platforms: list[str] | None) -> list[dict]:
    return [{**asdict(r), "status": r.status.value} for r in check_all(username, platforms)]


@mcp.tool()
def check_username(username: str, platforms: list[str] | None = None) -> list[dict]:
    """Check whether `username` exists on each platform.

    Args:
        username: handle to look up; a leading @ is ignored.
        platforms: subset of supported platforms (see list_platforms); default all.

    Returns one row per platform with status FOUND, NOT FOUND, UNKNOWN or INVALID,
    plus the profile URL.
    """
    return _rows(username, platforms)


@mcp.tool()
def check_usernames(usernames: list[str], platforms: list[str] | None = None) -> list[dict]:
    """Check several usernames (max 20 per call) on each platform."""
    if len(usernames) > 20:
        raise ValueError("at most 20 usernames per call; split the list")
    rows: list[dict] = []
    for name in usernames:
        rows += _rows(name, platforms)
    return rows


@mcp.tool()
def list_platforms() -> list[str]:
    """List the platforms handlecheck can query."""
    return sorted(PLATFORMS)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
