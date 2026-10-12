"""Wire the agents to the Campus Customs MCP server.

All shop facts and actions flow through the one MCP server (there is no second
shop-tools layer). This module builds a single shared toolset over that server
and an agent-facing view that hides the reserved `pay` tool — agents may prepare
payments but never execute them; `pay` is for the human-approval step.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastmcp.client import Client
from fastmcp.client.transports import StdioTransport
from pydantic_ai.mcp import MCPToolset

HW_DIR = Path(__file__).resolve().parent.parent
MCP_CONFIG_PATH = HW_DIR / ".mcp.json"

# Tools agents must never call directly — reserved for the human-approval step.
RESERVED_TOOLS = {"pay", "approve_purchase_order"}


def _server_command() -> tuple[str, list[str]]:
    """Read the campus-customs launch command from the project .mcp.json."""
    config = json.loads(MCP_CONFIG_PATH.read_text(encoding="utf-8"))
    entry = config["mcpServers"]["campus-customs"]
    return entry["command"], list(entry["args"])


def build_toolset() -> MCPToolset:
    """One MCP toolset over a single stdio connection, shared by all agents."""
    command, args = _server_command()
    transport = StdioTransport(command=command, args=args)
    return MCPToolset(Client(transport))


def agent_toolset(base: MCPToolset) -> MCPToolset:
    """The agent-facing view of the toolset: everything except reserved tools."""
    return base.filtered(lambda _ctx, tool: tool.name not in RESERVED_TOOLS)
