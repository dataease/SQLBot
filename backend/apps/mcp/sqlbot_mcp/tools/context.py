from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from apps.mcp.sqlbot_mcp import service
from apps.mcp.sqlbot_mcp.tools.base import ToolRuntime, run_tool


def register(mcp: FastMCP, runtime: ToolRuntime) -> None:
    @mcp.tool(name="agent_get_query_context")
    async def agent_get_query_context(
        datasource_id: Annotated[str, Field(description="Datasource id from agent_list_datasources")],
        question: Annotated[str, Field(description="The user's question in natural language")],
        keywords: Annotated[str | None, Field(
            description="Optional comma-separated business keywords you extracted from the question; "
                        "improves table and terminology matching")] = None,
    ) -> dict[str, Any]:
        """Get everything needed to write SQL for a question.

        Returns the database engine and version, the schema of the most relevant
        tables (only columns you may read), table relations, matching business
        terminology, similar question/SQL examples, custom instructions, and
        SQL writing rules. Call this before agent_execute_sql for every new
        question. No model is called; this is a lookup.
        """
        return await run_tool(
            runtime, "agent_get_query_context",
            lambda session, principal: service.get_query_context(session, principal, datasource_id, question,
                                                                 keywords),
        )
