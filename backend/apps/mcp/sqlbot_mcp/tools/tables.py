from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from apps.mcp.sqlbot_mcp import service
from apps.mcp.sqlbot_mcp.tools.base import ToolRuntime, run_tool


def register(mcp: FastMCP, runtime: ToolRuntime) -> None:
    @mcp.tool(name="agent_list_tables")
    async def agent_list_tables(
        datasource_id: Annotated[str, Field(description="Datasource id from agent_list_datasources")],
        keyword: Annotated[str | None, Field(
            description="Optional substring to filter table names and comments")] = None,
    ) -> dict[str, Any]:
        """List tables you can read in a datasource (names and comments only).

        Use this when agent_get_query_context did not include a table you need,
        then call agent_describe_tables for the tables you pick.
        """
        return await run_tool(
            runtime, "agent_list_tables",
            lambda session, principal: service.list_tables(session, principal, datasource_id, keyword),
        )

    @mcp.tool(name="agent_describe_tables")
    async def agent_describe_tables(
        datasource_id: Annotated[str, Field(description="Datasource id from agent_list_datasources")],
        table_names: Annotated[list[str], Field(description="Table names to describe", min_length=1,
                                                max_length=20)],
    ) -> dict[str, Any]:
        """Get columns and relations for specific tables.

        Only columns you may read are returned. Tables that do not exist or are
        not accessible are listed in `not_accessible`.
        """
        return await run_tool(
            runtime, "agent_describe_tables",
            lambda session, principal: service.describe_tables(session, principal, datasource_id, table_names),
        )
