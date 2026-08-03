"""Compatibility wrapper for the old finance-only MCP server module name."""

from __future__ import annotations

from .mcp_tool_server import *  # noqa: F403
from .mcp_tool_server import main


if __name__ == "__main__":
    main()
