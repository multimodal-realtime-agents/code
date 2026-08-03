"""Container entrypoint for Chapter 12 Cloud Run services."""

from __future__ import annotations

import os
import runpy


SERVICE_MODULES = {
    "frontend": "agent_system.frontend",
    "backend": "agent_system.backend",
    "a2a": "agent_system.stock_a2a_agent",
    "stock-a2a": "agent_system.stock_a2a_agent",
    "stock_a2a_agent": "agent_system.stock_a2a_agent",
    "weather": "agent_system.weather_a2a_agent",
    "weather-a2a": "agent_system.weather_a2a_agent",
    "weather_a2a_agent": "agent_system.weather_a2a_agent",
    "mcp": "agent_system.mcp_tool_server",
    "mcp-tool-server": "agent_system.mcp_tool_server",
    "mcp_tool_server": "agent_system.mcp_tool_server",
    "finance-mcp": "agent_system.finance_mcp_server",
    "finance_mcp_server": "agent_system.finance_mcp_server",
}


def main() -> None:
    service = os.getenv("AGENT_SYSTEM_SERVICE", "backend").strip().casefold()
    module = SERVICE_MODULES.get(service)
    if module is None:
        supported = ", ".join(sorted(SERVICE_MODULES))
        raise SystemExit(f"Unknown AGENT_SYSTEM_SERVICE={service!r}. Supported values: {supported}.")
    runpy.run_module(module, run_name="__main__")


if __name__ == "__main__":
    main()
