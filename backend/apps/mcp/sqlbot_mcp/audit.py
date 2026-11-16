"""Default audit sink: write tool calls to SQLBot's operation log (sys_logs).

Query results and SQL text are never stored here; the chat record keeps the
SQL for the owner. Rejections are recorded too, so repeated denials from one
token stand out.
"""

from datetime import datetime

from sqlmodel import Session

from apps.mcp.sqlbot_mcp.auth import AgentPrincipal
from apps.mcp.sqlbot_mcp.tools.base import AuditSink
from common.audit.models.log_model import (
    OperationModules,
    OperationStatus,
    OperationType,
    SystemLog,
)
from common.core.db import engine
from common.utils.utils import SQLBotLogUtil


class SystemLogAuditSink(AuditSink):
    def record(self, *, principal: AgentPrincipal, tool: str, ok: bool, duration_ms: int,
               detail: str | None = None, resource_id: str | None = None) -> None:
        user = principal.user
        log = SystemLog(
            operation_type=OperationType.EXECUTE_SQL.value if tool == "agent_execute_sql" else OperationType.VIEW.value,
            operation_detail=f"sqlbot-mcp {tool}",
            user_id=user.id,
            user_name=getattr(user, "name", None) or getattr(user, "account", None),
            operation_status=(OperationStatus.SUCCESS if ok else OperationStatus.FAILED).value,
            ip_address=principal.client_ip,
            execution_time=duration_ms,
            error_message=(detail or "")[:1000] or None,
            module=OperationModules.AGENT_MCP.value,
            oid=principal.oid,
            resource_id=resource_id,
            request_method="MCP",
            request_path=tool,
            create_time=datetime.now(),
            remark=f"{principal.credential_kind}:{principal.credential_id}",
        )
        try:
            with Session(engine) as session:
                session.add(log)
                session.commit()
        except Exception:
            SQLBotLogUtil.exception("[sqlbot-mcp] failed to write audit log")
