# Author: SQLBot
# Date: 2025/12/23
import json
import traceback
from typing import List, Optional

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from sqlmodel import Session

from apps.ai_model.model_factory import LLMConfig, LLMFactory
from apps.chat.curd.chat import start_log, end_log, save_table_select_answer
from apps.chat.models.chat_model import OperationEnum
from apps.template.select_table.generator import get_table_selection_template
from common.core.config import settings
from common.utils.utils import SQLBotLogUtil, extract_nested_json


def build_table_list_for_llm(table_objs: list) -> str:
    """
    构建 LLM 输入的表列表 JSON

    Args:
        table_objs: 表对象列表，每个对象包含 table 属性

    Returns:
        JSON 格式的表列表字符串
    """
    table_list = []
    for obj in table_objs:
        table = obj.table
        table_info = {
            "name": table.table_name,
            "comment": table.custom_comment.strip() if table.custom_comment else ""
        }
        table_list.append(table_info)
    return json.dumps(table_list, ensure_ascii=False)


def build_table_relations_str(ds_table_relation: list, table_objs: list) -> str:
    """
    构建表关系字符串

    Args:
        ds_table_relation: 数据源的表关系配置
        table_objs: 表对象列表

    Returns:
        表关系字符串，格式如：表1.字段1 = 表2.字段2
    """
    if not ds_table_relation:
        return ""

    # 构建 table_id -> table_name 映射
    table_dict = {}
    field_dict = {}
    for obj in table_objs:
        table = obj.table
        table_dict[table.id] = table.table_name
        if obj.fields:
            for field in obj.fields:
                field_dict[field.id] = field.field_name

    relations = list(filter(lambda x: x.get('shape') == 'edge', ds_table_relation))
    if not relations:
        return ""

    relation_lines = []
    for rel in relations:
        source_table_id = int(rel.get('source', {}).get('cell', 0))
        source_field_id = int(rel.get('source', {}).get('port', 0))
        target_table_id = int(rel.get('target', {}).get('cell', 0))
        target_field_id = int(rel.get('target', {}).get('port', 0))

        source_table = table_dict.get(source_table_id)
        source_field = field_dict.get(source_field_id)
        target_table = table_dict.get(target_table_id)
        target_field = field_dict.get(target_field_id)

        if source_table and source_field and target_table and target_field:
            relation_lines.append(f"{source_table}.{source_field} = {target_table}.{target_field}")

    return "\n".join(relation_lines)


def build_history_context(history_questions: List[str]) -> str:
    """
    构建历史问题上下文

    Args:
        history_questions: 历史问题列表

    Returns:
        格式化的历史问题字符串
    """
    if not history_questions:
        return "无"

    max_history = settings.MULTI_TURN_HISTORY_COUNT
    recent_history = history_questions[-max_history:] if history_questions else []

    if not recent_history:
        return "无"

    return "\n".join([f"- {q}" for q in recent_history])


def parse_llm_response(response_text: str, all_table_names: list) -> List[str]:
    """
    解析 LLM 返回的 JSON 响应

    Args:
        response_text: LLM 返回的文本
        all_table_names: 所有可用的表名列表（用于验证）

    Returns:
        选中的表名列表
    """
    try:
        json_str = extract_nested_json(response_text)
        if json_str:
            result = json.loads(json_str)
            if isinstance(result, dict) and 'tables' in result:
                selected_tables = result.get('tables', [])
                # 验证表名是否存在
                valid_tables = [t for t in selected_tables if t in all_table_names]
                return valid_tables
    except Exception as e:
        SQLBotLogUtil.error(f"Failed to parse LLM table selection response: {e}")

    return []


def calc_table_llm_selection(
        config: LLMConfig,
        table_objs: list,
        question: str,
        ds_table_relation: list = None,
        history_questions: List[str] = None,
        lang: str = "中文",
        session: Session = None,
        record_id: int = None
) -> List[str]:
    """
    使用 LLM 选择相关的表

    Args:
        config: LLM 配置
        table_objs: 表对象列表，每个对象包含 table 和 fields 属性
        question: 用户问题
        ds_table_relation: 数据源的表关系配置
        history_questions: 历史问题列表
        lang: 语言
        session: 数据库会话（用于记录日志）
        record_id: 记录ID（用于记录日志）

    Returns:
        选中的表名列表，失败时返回空列表
    """
    if not table_objs:
        return []

    current_log = None

    try:
        # 获取所有表名
        all_table_names = [obj.table.table_name for obj in table_objs]

        # 构建 LLM 输入
        table_list_str = build_table_list_for_llm(table_objs)
        table_relations_str = build_table_relations_str(ds_table_relation, table_objs)
        history_context = build_history_context(history_questions)

        # 获取提示词模板
        template = get_table_selection_template()
        system_prompt = template['system'].format(lang=lang)
        user_prompt = template['user'].format(
            table_list=table_list_str,
            table_relations=table_relations_str if table_relations_str else "无",
            history_questions=history_context,
            question=question
        )

        # 构建消息
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        # 记录日志 - 开始
        if session and record_id:
            current_log = start_log(
                session=session,
                ai_modal_id=config.model_id,
                ai_modal_name=config.model_name,
                operate=OperationEnum.SELECT_TABLE,
                record_id=record_id,
                full_message=[{'type': msg.type, 'content': msg.content} for msg in messages]
            )

        # 创建 LLM 实例并调用
        llm_instance = LLMFactory.create_llm(config)
        llm = llm_instance.llm

        SQLBotLogUtil.info(f"LLM table selection - question: {question}, tables count: {len(table_objs)}")

        # 非流式调用
        response = llm.invoke(messages)
        response_text = response.content if hasattr(response, 'content') else str(response)

        SQLBotLogUtil.info(f"LLM table selection response: {response_text}")

        # 记录日志 - 结束
        if session and record_id and current_log:
            messages.append(AIMessage(content=response_text))
            token_usage = {}
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                token_usage = dict(response.usage_metadata)
            end_log(
                session=session,
                log=current_log,
                full_message=[{'type': msg.type, 'content': msg.content} for msg in messages],
                reasoning_content=None,
                token_usage=token_usage
            )

        # 解析响应
        selected_tables = parse_llm_response(response_text, all_table_names)

        # 保存表选择结果到 ChatRecord
        if session and record_id:
            save_table_select_answer(session, record_id, response_text)

        if selected_tables:
            SQLBotLogUtil.info(f"LLM selected tables: {selected_tables}")
            return selected_tables
        else:
            SQLBotLogUtil.warning("LLM table selection failed: 暂时无法找到表")
            return []

    except Exception as e:
        SQLBotLogUtil.error(f"LLM table selection error: {e}")
        traceback.print_exc()
        return []
