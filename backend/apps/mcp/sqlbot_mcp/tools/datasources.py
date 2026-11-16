from typing import Any

from mcp.server.fastmcp import FastMCP

from apps.mcp.sqlbot_mcp import service
from apps.mcp.sqlbot_mcp.tools.base import ToolRuntime, run_tool


def register(mcp: FastMCP, runtime: ToolRuntime) -> None:
    @mcp.tool(name="agent_list_datasources")
    async def agent_list_datasources() -> list[dict[str, Any]]:
        """List the datasources you can query in SQLBot.

        Returns id, name, type, engine and description for each datasource.
        Use the id with the other agent_* tools.
        """
        return await run_tool(runtime, "agent_list_datasources",
                              lambda session, principal: service.list_datasources(session, principal))
