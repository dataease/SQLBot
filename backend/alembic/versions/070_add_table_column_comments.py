"""070_add_table_column_comments

为所有数据库表和字段添加中文备注（COMMENT ON）。
Revision ID: 070a1b2c3d4e5
Revises: 1f82cad3546e
Create Date: 2026-06-25 00:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '070a1b2c3d4e5'
down_revision = '1f82cad3546e'
branch_labels = None
depends_on = None

# 表和列备注定义：key 为 "表名" 或 "表名.列名"，value 为备注文本
_COMMENTS = {
    # ========== alembic_version 迁移版本记录表 ==========
    'alembic_version': 'Alembic迁移版本记录表',
    'alembic_version.version_num': '当前已应用的迁移版本号',

    # ========== sys_user 用户表 ==========
    'sys_user': '系统用户表',
    'sys_user.id': '用户ID',
    'sys_user.account': '用户账号',
    'sys_user.name': '用户名称',
    'sys_user.password': '用户密码',
    'sys_user.email': '用户邮箱',
    'sys_user.oid': '组织ID',
    'sys_user.status': '用户状态',
    'sys_user.origin': '用户来源',
    'sys_user.create_time': '创建时间',
    'sys_user.language': '用户语言偏好',
    'sys_user.system_variables': '用户自定义系统变量',

    # ========== sys_user_platform 用户平台关联表 ==========
    'sys_user_platform': '用户平台关联表',
    'sys_user_platform.id': '主键ID',
    'sys_user_platform.uid': '用户ID',
    'sys_user_platform.origin': '平台来源',
    'sys_user_platform.platform_uid': '平台用户ID',

    # ========== ai_model AI模型表 ==========
    'ai_model': 'AI模型配置表',
    'ai_model.id': '模型ID',
    'ai_model.supplier': '模型供应商',
    'ai_model.name': '模型名称',
    'ai_model.model_type': '模型类型',
    'ai_model.base_model': '基础模型标识',
    'ai_model.default_model': '是否默认模型',
    'ai_model.api_key': 'API密钥',
    'ai_model.api_domain': 'API域名地址',
    'ai_model.protocol': '通信协议',
    'ai_model.config': '模型配置信息',
    'ai_model.status': '模型状态',
    'ai_model.create_time': '创建时间',

    # ========== ai_model_workspace_mapping 模型工作空间映射表 ==========
    'ai_model_workspace_mapping': 'AI模型与工作空间映射表',
    'ai_model_workspace_mapping.id': '主键ID',
    'ai_model_workspace_mapping.ai_model_id': 'AI模型ID',
    'ai_model_workspace_mapping.workspace_id': '工作空间ID',

    # ========== sys_workspace 工作空间表 ==========
    'sys_workspace': '工作空间表',
    'sys_workspace.id': '工作空间ID',
    'sys_workspace.name': '工作空间名称',
    'sys_workspace.create_time': '创建时间',

    # ========== sys_user_ws 用户工作空间关联表 ==========
    'sys_user_ws': '用户工作空间权限表',
    'sys_user_ws.id': '主键ID',
    'sys_user_ws.uid': '用户ID',
    'sys_user_ws.oid': '组织ID',
    'sys_user_ws.weight': '权重值',

    # ========== sys_assistant AI助手表 ==========
    'sys_assistant': 'AI助手配置表',
    'sys_assistant.id': '助手ID',
    'sys_assistant.name': '助手名称',
    'sys_assistant.type': '助手类型',
    'sys_assistant.domain': '助手适用领域',
    'sys_assistant.description': '助手描述信息',
    'sys_assistant.configuration': '助手配置',
    'sys_assistant.create_time': '创建时间',
    'sys_assistant.app_id': '应用ID',
    'sys_assistant.app_secret': '应用密钥',
    'sys_assistant.oid': '组织ID',
    'sys_assistant.enable_custom_model': '是否启用自定义模型',
    'sys_assistant.custom_model': '自定义模型名称',

    # ========== sys_authentication 认证配置表 ==========
    'sys_authentication': '认证配置表',
    'sys_authentication.id': '认证配置ID',
    'sys_authentication.name': '认证配置名称',
    'sys_authentication.type': '认证类型',
    'sys_authentication.config': '认证配置详情',
    'sys_authentication.create_time': '创建时间',
    'sys_authentication.enable': '是否启用',
    'sys_authentication.valid': '配置是否有效',

    # ========== sys_apikey API密钥表 ==========
    'sys_apikey': 'API密钥表',
    'sys_apikey.id': '密钥ID',
    'sys_apikey.access_key': '访问密钥',
    'sys_apikey.secret_key': '密钥',
    'sys_apikey.create_time': '创建时间',
    'sys_apikey.uid': '绑定用户ID',
    'sys_apikey.status': '密钥状态',

    # ========== system_variable 系统变量表 ==========
    'system_variable': '系统变量表',
    'system_variable.id': '变量ID',
    'system_variable.name': '变量名称',
    'system_variable.var_type': '变量数据类型',
    'system_variable.type': '变量分类',
    'system_variable.value': '变量值',
    'system_variable.create_time': '创建时间',
    'system_variable.create_by': '创建人ID',

    # ========== terms 术语设置表 ==========
    'terms': '术语设置表',
    'terms.id': '术语ID',
    'terms.term': '术语名称',
    'terms.definition': '术语定义',
    'terms.domain': '所属领域',
    'terms.create_time': '创建时间',

    # ========== custom_prompt 自定义提示词表 ==========
    'custom_prompt': '自定义提示词表',
    'custom_prompt.id': '提示词ID',
    'custom_prompt.oid': '组织ID',
    'custom_prompt.type': '提示词类型',
    'custom_prompt.create_time': '创建时间',
    'custom_prompt.name': '提示词名称',
    'custom_prompt.prompt': '提示词内容',
    'custom_prompt.specific_ds': '是否关联特定数据源',
    'custom_prompt.datasource_ids': '关联数据源ID列表',
    'custom_prompt.advanced_application': '高级应用ID',

    # ========== core_datasource 数据源表 ==========
    'core_datasource': '数据源配置表',
    'core_datasource.id': '数据源ID',
    'core_datasource.name': '数据源名称',
    'core_datasource.description': '数据源描述',
    'core_datasource.type': '数据源类型',
    'core_datasource.type_name': '数据源类型名称',
    'core_datasource.configuration': '连接配置信息',
    'core_datasource.create_time': '创建时间',
    'core_datasource.create_by': '创建人ID',
    'core_datasource.status': '连接状态',
    'core_datasource.num': '数据源编号',
    'core_datasource.oid': '组织ID',
    'core_datasource.table_relation': '表关系配置',
    'core_datasource.embedding': '向量嵌入信息',
    'core_datasource.recommended_config': '推荐问题配置',

    # ========== core_table 数据源表信息 ==========
    'core_table': '数据源表信息',
    'core_table.id': '表记录ID',
    'core_table.ds_id': '所属数据源ID',
    'core_table.checked': '是否启用',
    'core_table.table_name': '表名称',
    'core_table.table_comment': '表注释',
    'core_table.custom_comment': '自定义表注释',
    'core_table.embedding': '表向量嵌入信息',

    # ========== ds_recommended_problem 推荐问题表 ==========
    'ds_recommended_problem': '数据源推荐问题表',
    'ds_recommended_problem.id': '问题ID',
    'ds_recommended_problem.datasource_id': '数据源ID',
    'ds_recommended_problem.question': '推荐问题内容',
    'ds_recommended_problem.remark': '问题备注',
    'ds_recommended_problem.sort': '排序序号',
    'ds_recommended_problem.create_time': '创建时间',
    'ds_recommended_problem.create_by': '创建人ID',

    # ========== core_field 数据源字段信息 ==========
    'core_field': '数据源字段信息表',
    'core_field.id': '字段记录ID',
    'core_field.ds_id': '所属数据源ID',
    'core_field.table_id': '所属表ID',
    'core_field.checked': '是否启用',
    'core_field.field_name': '字段名称',
    'core_field.field_type': '字段类型',
    'core_field.field_comment': '字段注释',
    'core_field.custom_comment': '自定义字段注释',
    'core_field.field_index': '字段序号',

    # ========== data_training 数据训练（示例库）表 ==========
    'data_training': 'SQL示例训练库表',
    'data_training.id': '训练记录ID',
    'data_training.oid': '组织ID',
    'data_training.datasource': '关联数据源ID',
    'data_training.create_time': '创建时间',
    'data_training.question': '训练问题',
    'data_training.description': '训练描述',
    'data_training.embedding': '向量嵌入数据',
    'data_training.enabled': '是否启用',
    'data_training.advanced_application': '高级应用ID',

    # ========== terminology 术语表 ==========
    'terminology': '术语管理表',
    'terminology.id': '术语ID',
    'terminology.oid': '组织ID',
    'terminology.pid': '父级术语ID',
    'terminology.create_time': '创建时间',
    'terminology.word': '术语词条',
    'terminology.description': '术语描述',
    'terminology.embedding': '向量嵌入数据',
    'terminology.specific_ds': '是否关联特定数据源',
    'terminology.datasource_ids': '关联数据源ID列表',
    'terminology.enabled': '是否启用',
    'terminology.advanced_application': '高级应用ID',

    # ========== core_dashboard 仪表板表 ==========
    'core_dashboard': '仪表板表',
    'core_dashboard.id': '仪表板ID',
    'core_dashboard.name': '仪表板名称',
    'core_dashboard.pid': '父级仪表板ID',
    'core_dashboard.workspace_id': '所属工作空间ID',
    'core_dashboard.org_id': '组织ID',
    'core_dashboard.level': '层级',
    'core_dashboard.node_type': '节点类型',
    'core_dashboard.type': '仪表板类型',
    'core_dashboard.canvas_style_data': '画布样式数据',
    'core_dashboard.component_data': '组件数据',
    'core_dashboard.canvas_view_info': '画布视图信息',
    'core_dashboard.mobile_layout': '是否移动端布局',
    'core_dashboard.status': '状态',
    'core_dashboard.self_watermark_status': '水印状态',
    'core_dashboard.sort': '排序序号',
    'core_dashboard.create_time': '创建时间',
    'core_dashboard.create_by': '创建人',
    'core_dashboard.update_time': '更新时间',
    'core_dashboard.update_by': '更新人',
    'core_dashboard.remark': '备注',
    'core_dashboard.source': '来源标识',
    'core_dashboard.delete_flag': '删除标记',
    'core_dashboard.delete_time': '删除时间',
    'core_dashboard.delete_by': '删除人',
    'core_dashboard.version': '版本号',
    'core_dashboard.content_id': '内容ID',
    'core_dashboard.check_version': '检查版本',

    # ========== chat_log 聊天日志表 ==========
    'chat_log': 'AI聊天执行日志表',
    'chat_log.id': '日志ID',
    'chat_log.type': '聊天类型',
    'chat_log.operate': '操作类型',
    'chat_log.pid': '父级日志ID',
    'chat_log.ai_modal_id': '使用的AI模型ID',
    'chat_log.base_modal': '基础模型标识',
    'chat_log.messages': '消息内容',
    'chat_log.reasoning_content': '推理内容',
    'chat_log.start_time': '开始时间',
    'chat_log.finish_time': '结束时间',
    'chat_log.token_usage': 'Token消耗统计',
    'chat_log.local_operation': '是否本地操作',
    'chat_log.error': '是否发生错误',

    # ========== chat 聊天主表 ==========
    'chat': 'AI聊天会话表',
    'chat.id': '聊天会话ID',
    'chat.oid': '组织ID',
    'chat.create_time': '创建时间',
    'chat.create_by': '创建人ID',
    'chat.brief': '会话摘要',
    'chat.chat_type': '聊天类型',
    'chat.datasource': '关联数据源ID',
    'chat.engine_type': '数据引擎类型',
    'chat.origin': '会话来源',
    'chat.brief_generate': '是否已生成摘要',
    'chat.recommended_question_answer': '推荐问题回答',
    'chat.recommended_question': '推荐问题内容',
    'chat.recommended_generate': '是否已生成推荐问题',

    # ========== chat_record 聊天记录表 ==========
    'chat_record': 'AI聊天记录表',
    'chat_record.id': '记录ID',
    'chat_record.chat_id': '关联聊天会话ID',
    'chat_record.ai_modal_id': '使用的AI模型ID',
    'chat_record.first_chat': '是否首轮对话',
    'chat_record.create_time': '创建时间',
    'chat_record.finish_time': '完成时间',
    'chat_record.create_by': '创建人ID',
    'chat_record.datasource': '关联数据源ID',
    'chat_record.engine_type': '数据引擎类型',
    'chat_record.question': '用户问题内容',
    'chat_record.sql_answer': 'SQL生成回答',
    'chat_record.sql': '生成的SQL语句',
    'chat_record.sql_exec_result': 'SQL执行结果',
    'chat_record.data': '查询返回数据',
    'chat_record.chart_answer': '图表生成回答',
    'chat_record.chart': '图表配置信息',
    'chat_record.analysis': '分析结果内容',
    'chat_record.predict': '预测结果内容',
    'chat_record.predict_data': '预测数据',
    'chat_record.recommended_question_answer': '推荐问题回答',
    'chat_record.recommended_question': '推荐问题列表',
    'chat_record.datasource_select_answer': '数据源选择回答',
    'chat_record.finish': '是否已完成',
    'chat_record.error': '错误信息',
    'chat_record.analysis_record_id': '关联分析记录ID',
    'chat_record.predict_record_id': '关联预测记录ID',
    'chat_record.regenerate_record_id': '关联重新生成记录ID',

    # ========== sys_logs 系统操作日志表 ==========
    'sys_logs': '系统操作日志表',
    'sys_logs.id': '日志ID',
    'sys_logs.operation_type': '操作类型',
    'sys_logs.operation_detail': '操作详情',
    'sys_logs.user_id': '操作用户ID',
    'sys_logs.operation_status': '操作状态',
    'sys_logs.ip_address': '操作IP地址',
    'sys_logs.user_agent': '用户代理信息',
    'sys_logs.execution_time': '执行耗时',
    'sys_logs.error_message': '错误信息',
    'sys_logs.create_time': '创建时间',
    'sys_logs.module': '操作模块',
    'sys_logs.oid': '组织ID',
    'sys_logs.resource_id': '操作资源ID',
    'sys_logs.request_method': '请求方法',
    'sys_logs.request_path': '请求路径',
    'sys_logs.remark': '备注',
    'sys_logs.user_name': '操作用户名称',
    'sys_logs.resource_name': '操作资源名称',

    # ========== sys_logs_resource 日志关联资源表 ==========
    'sys_logs_resource': '操作日志关联资源表',
    'sys_logs_resource.id': '主键ID',
    'sys_logs_resource.log_id': '关联日志ID',
    'sys_logs_resource.resource_id': '资源ID',
    'sys_logs_resource.resource_name': '资源名称',
    'sys_logs_resource.module': '资源模块',

    # ========== ds_permission 数据权限表 ==========
    'ds_permission': '数据权限配置表',
    'ds_permission.id': '权限ID',
    'ds_permission.enable': '是否启用',
    'ds_permission.name': '权限名称',
    'ds_permission.auth_target_type': '授权对象类型',
    'ds_permission.auth_target_id': '授权对象ID',
    'ds_permission.type': '权限类型',
    'ds_permission.ds_id': '数据源ID',
    'ds_permission.table_id': '表ID',
    'ds_permission.expression_tree': '权限表达式树',
    'ds_permission.permissions': '权限配置',
    'ds_permission.white_list_user': '白名单用户列表',
    'ds_permission.create_time': '创建时间',

    # ========== ds_rules 数据规则表 ==========
    'ds_rules': '数据规则组表',
    'ds_rules.id': '规则组ID',
    'ds_rules.enable': '是否启用',
    'ds_rules.name': '规则组名称',
    'ds_rules.description': '规则组描述',
    'ds_rules.permission_list': '权限列表',
    'ds_rules.user_list': '用户列表',
    'ds_rules.white_list_user': '白名单用户列表',
    'ds_rules.oid': '组织ID',
    'ds_rules.create_time': '创建时间',

    # ========== license 许可证表 ==========
    'license': '系统许可证表',
    'license.id': '许可证ID',
    'license.license_key': '许可证密钥',
    'license.f2c_license': 'F2C许可证信息',
    'license.create_time': '创建时间',
    'license.update_time': '更新时间',

    # ========== rsa 密钥表 ==========
    'rsa': 'RSA密钥存储表',
    'rsa.id': '密钥ID',
    'rsa.private_key': 'RSA私钥',
    'rsa.public_key': 'RSA公钥',
    'rsa.salt': '加密盐值',
    'rsa.create_time': '创建时间',
    'rsa.update_time': '更新时间',

    # ========== sys_arg 系统参数表 ==========
    'sys_arg': '系统参数配置表',
    'sys_arg.id': '参数ID',
    'sys_arg.pkey': '参数键',
    'sys_arg.pval': '参数值',
    'sys_arg.ptype': '参数类型',
    'sys_arg.sort_no': '排序序号',

    # ========== sys_platform_token 平台令牌表 ==========
    'sys_platform_token': '平台认证令牌表',
    'sys_platform_token.id': '令牌ID',
    'sys_platform_token.token': '令牌值',
    'sys_platform_token.create_time': '创建时间',
    'sys_platform_token.exp_time': '过期时间',
}


def _escape_comment(comment):
    return comment.replace("'", "''")


def _apply_table_comment(table, comment):
    if comment is None:
        op.execute(f"COMMENT ON TABLE {table} IS NULL")
    else:
        op.execute(f"COMMENT ON TABLE {table} IS '{_escape_comment(comment)}'")


def _apply_column_comment(table, column, comment):
    if comment is None:
        op.execute(f"COMMENT ON COLUMN {table}.{column} IS NULL")
    else:
        op.execute(f"COMMENT ON COLUMN {table}.{column} IS '{_escape_comment(comment)}'")


def upgrade():
    """为所有表和字段添加中文备注"""
    table_keys = sorted(k for k in _COMMENTS if '.' not in k)
    column_keys = sorted(k for k in _COMMENTS if '.' in k)

    for table in table_keys:
        _apply_table_comment(table, _COMMENTS[table])

    for key in column_keys:
        table, column = key.split('.', 1)
        _apply_column_comment(table, column, _COMMENTS[key])


def downgrade():
    """移除所有表和字段的备注"""
    table_keys = sorted((k for k in _COMMENTS if '.' not in k), reverse=True)
    column_keys = sorted((k for k in _COMMENTS if '.' in k), reverse=True)

    for key in column_keys:
        table, column = key.split('.', 1)
        _apply_column_comment(table, column, None)

    for table in table_keys:
        _apply_table_comment(table, None)
