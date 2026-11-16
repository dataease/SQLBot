"""Business logic behind the SQLBot MCP tools.

Every function takes an ``AgentPrincipal`` and a database ``Session`` and is
synchronous; tools run them in a worker thread. No function here calls a model.
Datasource ids outside the caller's reach and missing ids raise the same
``ToolError`` so ids cannot be probed.
"""

from dataclasses import dataclass
from typing import Any

import orjson
from sqlmodel import Session, select

from apps.chat.curd.chat import (
    create_chat,
    finish_record,
    save_error_message,
    save_question,
    save_sql,
    save_sql_exec_data,
)
from apps.chat.models.chat_model import Chat, ChatQuestion, CreateChat
from apps.data_training.curd.data_training import get_training_template
from apps.datasource.crud.datasource import (
    get_datasource_list,
    get_table_obj_by_ds,
    get_table_schema,
)
from apps.datasource.crud.permission import get_row_permission_filters, is_normal_user
from apps.datasource.models.datasource import CoreDatasource
from apps.db.db import check_connection, exec_sql, get_version
from apps.db.sql_guard import (
    AGENT,
    SqlRejected,
    TableAccess,
    build_context,
    get_pipeline,
)
from apps.mcp.sqlbot_mcp.auth import AgentPrincipal
from apps.terminology.curd.terminology import (
    expand_with_terminology,
    get_terminology_template,
)
from common.core.embedding_config import load_embedding_config
from common.utils.data_format import DataFormat
from common.utils.utils import SQLBotLogUtil, prepare_for_orjson

DEFAULT_MAX_ROWS = 200
MAX_ROWS_LIMIT = 1000
STATEMENT_TIMEOUT_SECONDS = 30
LIST_TABLES_LIMIT = 200
# Chat.origin values: 0 page, 1 mcp, 2 assistant.
CHAT_ORIGIN_MCP = 1

SQL_WRITING_RULES = (
    "Write exactly one read-only SELECT (or WITH ... SELECT) statement for the given engine. "
    "Use only tables and columns listed in `schema`; columns that are not listed are not accessible. "
    "List columns explicitly instead of SELECT * on tables with restricted columns. "
    "Do not use locking clauses, table functions or system catalogs. "
    "Row-level permissions and a row cap are applied by SQLBot automatically."
)


class ToolError(Exception):
    """Expected failure; ``message`` is safe to show to the agent."""

    def __init__(self, message: str, *, code: str = "error"):
        super().__init__(message)
        self.message = message
        self.code = code


NOT_FOUND = "Datasource not found or not accessible"


@dataclass
class ResolvedDatasource:
    ds: CoreDatasource
    engine: str


# --- access ------------------------------------------------------------------

def accessible_datasources(session: Session, principal: AgentPrincipal) -> list[CoreDatasource]:
    datasources = get_datasource_list(session=session, user=principal.user)
    return [ds for ds in datasources if principal.allows_datasource(ds.id)]


def resolve_datasource(session: Session, principal: AgentPrincipal, datasource_id: Any) -> ResolvedDatasource:
    try:
        ds_id = int(datasource_id)
    except (TypeError, ValueError):
        raise ToolError(NOT_FOUND, code="not_found")
    if not principal.allows_datasource(ds_id):
        raise ToolError(NOT_FOUND, code="not_found")
    ds = session.get(CoreDatasource, ds_id)
    if ds is None or ds.oid != principal.oid:
        raise ToolError(NOT_FOUND, code="not_found")
    engine_name = "PostgreSQL" if ds.type == "excel" else (ds.type_name or ds.type)
    return ResolvedDatasource(ds=ds, engine=engine_name)


def _engine_with_version(resolved: ResolvedDatasource) -> str:
    try:
        return f"{resolved.engine} {get_version(resolved.ds)}".strip()
    except Exception:
        return resolved.engine


# --- list_datasources --------------------------------------------------------

def list_datasources(session: Session, principal: AgentPrincipal) -> list[dict]:
    return [
        {"id": str(ds.id), "name": ds.name, "type": ds.type,
         "engine": "PostgreSQL" if ds.type == "excel" else (ds.type_name or ds.type),
         "description": ds.description or ""}
        for ds in accessible_datasources(session, principal)
    ]


# --- tables ------------------------------------------------------------------

def _table_comment(table) -> str:
    return ((table.custom_comment or "").strip() or (table.table_comment or "").strip())


def list_tables(session: Session, principal: AgentPrincipal, datasource_id: Any,
                keyword: str | None = None) -> dict:
    resolved = resolve_datasource(session, principal, datasource_id)
    needle = (keyword or "").strip().lower()
    items = []
    for obj in get_table_obj_by_ds(session=session, current_user=principal.user, ds=resolved.ds):
        comment = _table_comment(obj.table)
        if needle and needle not in obj.table.table_name.lower() and needle not in comment.lower():
            continue
        items.append({"table_name": obj.table.table_name, "comment": comment})
    total = len(items)
    return {"datasource_id": str(resolved.ds.id), "total": total, "truncated": total > LIST_TABLES_LIMIT,
            "tables": items[:LIST_TABLES_LIMIT]}


def describe_tables(session: Session, principal: AgentPrincipal, datasource_id: Any,
                    table_names: list[str]) -> dict:
    resolved = resolve_datasource(session, principal, datasource_id)
    wanted = [str(name) for name in (table_names or []) if str(name).strip()]
    if not wanted:
        raise ToolError("table_names must not be empty", code="invalid_argument")
    schema, found = get_table_schema(session, principal.user, resolved.ds, "", embedding=False, table_list=wanted)
    found_set = {name.lower() for name in found}
    return {
        "datasource_id": str(resolved.ds.id),
        "engine": _engine_with_version(resolved),
        "schema": schema,
        "tables": found,
        # Missing and forbidden tables look the same.
        "not_accessible": [name for name in wanted if name.lower() not in found_set],
    }


# --- query context -----------------------------------------------------------

def _custom_prompt(session: Session, principal: AgentPrincipal, ds_id: int) -> str:
    try:
        from sqlbot_xpack.custom_prompt.curd.custom_prompt import find_custom_prompts
        from sqlbot_xpack.custom_prompt.models.custom_prompt_model import (
            CustomPromptTypeEnum,
        )
        from sqlbot_xpack.license.license_manage import SQLBotLicenseUtil
    except Exception:  # pragma: no cover - xpack is a hard dependency
        return ""
    if not SQLBotLicenseUtil.valid():
        return ""
    prompt, _ = find_custom_prompts(session, CustomPromptTypeEnum.GENERATE_SQL, principal.oid, ds_id)
    return prompt or ""


def get_query_context(session: Session, principal: AgentPrincipal, datasource_id: Any, question: str,
                      keywords: str | None = None) -> dict:
    question = (question or "").strip()
    if not question:
        raise ToolError("question must not be empty", code="invalid_argument")
    resolved = resolve_datasource(session, principal, datasource_id)
    ds = resolved.ds
    config = load_embedding_config(session)
    keywords = ",".join(k.strip() for k in (keywords or "").split(",") if k.strip()) or None
    expanded = expand_with_terminology(keywords, session, principal.oid, ds.id) if keywords else None

    schema, tables = get_table_schema(session, principal.user, ds, question, keywords=expanded, config=config)
    terminology, term_list = get_terminology_template(session, keywords or question, principal.oid, ds.id,
                                                      config=config)
    training, example_list = get_training_template(session, question, principal.oid, ds.id, config=config)
    return {
        "datasource_id": str(ds.id),
        "engine": _engine_with_version(resolved),
        "schema": schema,
        "tables": tables,
        "terminologies": term_list,
        "sql_examples": example_list,
        "custom_prompt": _custom_prompt(session, principal, ds.id),
        "rules": SQL_WRITING_RULES,
        "more_tables_hint": "If a needed table is missing, call agent_list_tables and agent_describe_tables.",
    }


# --- execute -----------------------------------------------------------------

def table_access_for(session: Session, principal: AgentPrincipal, ds: CoreDatasource) -> dict[str, TableAccess]:
    """Tables the caller may read, with visible columns and row filters."""
    objs = get_table_obj_by_ds(session=session, current_user=principal.user, ds=ds)
    if not objs:
        return {}
    normal = is_normal_user(principal.user)
    filters = {}
    if normal:
        names = [obj.table.table_name for obj in objs]
        for item in get_row_permission_filters(session=session, current_user=principal.user, ds=ds, tables=names):
            filters[item["table"].lower()] = item["filter"]

    from apps.datasource.models.datasource import CoreField
    table_ids = [obj.table.id for obj in objs]
    checked = session.exec(select(CoreField.table_id, CoreField.field_name)
                           .where(CoreField.table_id.in_(table_ids), CoreField.checked == True)).all()  # noqa: E712
    all_columns: dict[int, set[str]] = {}
    for table_id, field_name in checked:
        all_columns.setdefault(table_id, set()).add(field_name.lower())

    access = {}
    for obj in objs:
        name = obj.table.table_name.lower()
        visible = frozenset(f.field_name.lower() for f in (obj.fields or []))
        known = frozenset(all_columns.get(obj.table.id, set()))
        restricted = normal and visible != known
        access[name] = TableAccess(
            name=name,
            visible_columns=visible if restricted else None,
            all_columns=known,
            row_filter=filters.get(name),
            schema=(obj.schema or "").lower() if ds.type not in ("mysql", "doris", "starrocks", "hive") else "",
        )
    return access


def _chat_for(session: Session, principal: AgentPrincipal, ds: CoreDatasource, chat_id: Any,
              question: str) -> int:
    if chat_id:
        try:
            chat = session.get(Chat, int(chat_id))
        except (TypeError, ValueError):
            chat = None
        if chat is None or chat.create_by != principal.user.id or chat.oid != principal.oid \
                or (chat.datasource and int(chat.datasource) != ds.id):
            raise ToolError("Chat not found or not accessible", code="not_found")
        return chat.id
    info = create_chat(session, principal.user,
                       CreateChat(origin=CHAT_ORIGIN_MCP, datasource=ds.id, question=question[:200]),
                       require_datasource=False)
    return info.id


def execute_sql(session: Session, principal: AgentPrincipal, datasource_id: Any, sql: str, question: str,
                chat_id: Any = None, max_rows: int | None = None) -> dict:
    sql = (sql or "").strip()
    question = (question or "").strip()
    if not sql:
        raise ToolError("sql must not be empty", code="invalid_argument")
    if not question:
        raise ToolError("question must not be empty", code="invalid_argument")
    limit = max(1, min(int(max_rows or DEFAULT_MAX_ROWS), MAX_ROWS_LIMIT))

    resolved = resolve_datasource(session, principal, datasource_id)
    ds = resolved.ds
    tables = table_access_for(session, principal, ds)
    try:
        ctx = build_context(sql.rstrip(";").strip(), ds.type, tables=tables, max_rows=limit, strict=True)
        final_sql = get_pipeline(AGENT).run(ctx)
    except SqlRejected as e:
        raise ToolError(e.reason, code=e.code)

    if not check_connection(trans=None, ds=ds):
        raise ToolError("Datasource connection failed", code="connection_failed")

    chat_id = _chat_for(session, principal, ds, chat_id, question)
    record = save_question(session, principal.user, ChatQuestion(chat_id=chat_id, question=question))
    # The record keeps the agent's SQL; the permission-rewritten SQL is not
    # stored or returned so row rules are not disclosed.
    save_sql(session, record.id, sql)
    try:
        result = exec_sql(ds=ds, sql=final_sql, origin_column=False,
                          timeout_seconds=STATEMENT_TIMEOUT_SECONDS, max_rows=limit + 1)
    except Exception as e:
        message = str(e).splitlines()[0][:500] if str(e) else type(e).__name__
        save_error_message(session, record.id, orjson.dumps({"message": message, "type": "exec-sql-err"}).decode())
        SQLBotLogUtil.warning(f"[sqlbot-mcp] execute failed record={record.id}: {message}")
        raise ToolError(f"SQL execution failed: {message}", code="execution_failed")

    rows = result.get("data") or []
    truncated = len(rows) > limit
    rows = rows[:limit]
    rows = DataFormat.normalize_qualified_sql_column_keys_in_object_array(
        DataFormat.convert_large_numbers_in_object_array(rows))
    stored = {"fields": result.get("fields"), "fields_info": result.get("fields_info"),
              "data": prepare_for_orjson(rows), "datasource": ds.id}
    if truncated:
        stored["limit"] = limit
    save_sql_exec_data(session, record.id, orjson.dumps(stored).decode())
    finish_record(session, record.id)
    return {
        "chat_id": str(chat_id),
        "record_id": str(record.id),
        "fields": result.get("fields"),
        "data": rows,
        "row_count": len(rows),
        "truncated": truncated,
        "row_permission_applied": bool(ctx.notes.get("row_permission_applied")),
    }
