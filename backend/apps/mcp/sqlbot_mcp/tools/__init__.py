"""Tool registry for the SQLBot MCP server.

To add a tool: create a module with ``register(mcp, runtime)`` and append it
to ``TOOL_MODULES``. The server and the other tools stay unchanged.
"""

from mcp.server.fastmcp import FastMCP

from apps.mcp.sqlbot_mcp.tools import context, datasources, execute, tables
from apps.mcp.sqlbot_mcp.tools.base import ToolRuntime

TOOL_MODULES = (datasources, context, tables, execute)


def register_tools(mcp: FastMCP, runtime: ToolRuntime, modules=TOOL_MODULES) -> None:
    for module in modules:
        module.register(mcp, runtime)
