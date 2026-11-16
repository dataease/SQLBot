from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from apps.mcp.sqlbot_mcp import service
from apps.mcp.sqlbot_mcp.tools.base import ToolRuntime, run_tool


def register(mcp: FastMCP, runtime: ToolRuntime) -> None:
    @mcp.tool(name="agent_execute_sql")
    async def agent_execute_sql(
        datasource_id: Annotated[str, Field(description="Datasource id from agent_list_datasources")],
        sql: Annotated[str, Field(description="One read-only SELECT statement in the datasource's dialect")],
        question: Annotated[str, Field(description="The question this SQL answers; stored in SQLBot history")],
        chat_id: Annotated[str | None, Field(
            description="chat_id from a previous agent_execute_sql call to continue the same conversation")] = None,
        max_rows: Annotated[int | None, Field(
            description=f"Maximum rows to return (default {service.DEFAULT_MAX_ROWS}, "
                        f"at most {service.MAX_ROWS_LIMIT})", ge=1, le=service.MAX_ROWS_LIMIT)] = None,
    ) -> dict[str, Any]:
        """Validate and run one read-only SQL query, and save it to SQLBot history.

        SQLBot rejects SQL that writes, locks, calls unsafe functions, or reads
        tables/columns you may not access, and explains why; fix the SQL and
        retry. Row permissions and a row cap are applied automatically.
        Prefer aggregated queries over large detail queries. Returns columns,
        rows, `truncated`, and `chat_id`/`record_id`.
        """
        return await run_tool(
            runtime, "agent_execute_sql",
            lambda session, principal: service.execute_sql(session, principal, datasource_id, sql, question,
                                                           chat_id, max_rows),
            audit=True, heavy=True, resource_id=lambda result: result.get("record_id") if result else None,
        )
