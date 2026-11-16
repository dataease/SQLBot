import os
import sys
import threading
from concurrent.futures import Future
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import orjson

# Ensure backend root is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from apps.chat.models.chat_model import ChatQuestion, OperationEnum  # noqa: E402
from apps.chat.task import llm as llm_module  # noqa: E402
from apps.chat.task.llm import LLMService, parse_analysis_plan  # noqa: E402
from apps.datasource.models.datasource import CoreDatasource  # noqa: E402

REPO_ROOT = os.path.dirname(backend_dir)


def _plan(*queries):
    return orjson.dumps({'queries': list(queries)}).decode()


# ---------- parse_analysis_plan ----------

def test_parse_plan_extracts_queries_and_strips_semicolon():
    text = '说明\n' + _plan({'purpose': ' 占比 ', 'sql': ' SELECT 1; '})
    assert parse_analysis_plan(text, 3) == [{'purpose': '占比', 'sql': 'SELECT 1'}]


def test_parse_plan_respects_max_queries():
    text = _plan(*[{'purpose': str(i), 'sql': f'SELECT {i}'} for i in range(5)])
    assert len(parse_analysis_plan(text, 2)) == 2
    assert parse_analysis_plan(text, 0) == []


def test_parse_plan_drops_invalid_items():
    text = _plan({'purpose': 'no sql'}, {'sql': ''}, {'sql': 123}, 'raw', {'sql': 'SELECT 2'})
    assert parse_analysis_plan(text, 5) == [{'purpose': '', 'sql': 'SELECT 2'}]


def test_parse_plan_handles_non_json_and_empty():
    assert parse_analysis_plan('不需要补充查询', 3) == []
    assert parse_analysis_plan(_plan(), 3) == []
    assert parse_analysis_plan('{"queries": "SELECT 1"}', 3) == []


# ---------- templates ----------

def test_analysis_templates_format_without_errors():
    q = ChatQuestion(chat_id=1, question='4月比3月变化多少？')
    q.sql = 'SELECT 1'
    q.fields = '["a"]'
    q.data = '[{"a": 1}]'
    q.data_row_count = 1
    q.analysis_schema = '# Table: orders'
    q.engine = 'PostgreSQL'

    system = q.analysis_sys_question()
    user = q.analysis_user_question()
    plan_system = q.analysis_plan_sys_question(3)
    plan_user = q.analysis_plan_user_question()

    assert '不得自行计算' in system
    assert '4月比3月变化多少？' in user and 'SELECT 1' in user
    assert '最多 3 条' in plan_system and '{"queries":[]}' in plan_system
    assert 'row-count="1"' in plan_user


# ---------- execute_analysis_query: same guards as main flow ----------

def _service(table_names=('orders',)):
    service = LLMService.__new__(LLMService)
    service.ds = CoreDatasource(id=1, name='ds', type='pg', oid=1)
    service.table_name_list = list(table_names)
    service.record = SimpleNamespace(id=10)
    return service


@patch.object(llm_module, 'trigger_log_error')
@patch.object(llm_module, 'end_log')
@patch.object(llm_module, 'start_log', return_value=SimpleNamespace(id=1))
def test_execute_query_rejects_unauthorized_table(_start, _end, trigger):
    service = _service()
    service.execute_sql = MagicMock()

    result = service.execute_analysis_query(MagicMock(), {'purpose': 'x', 'sql': 'SELECT * FROM sys_user'})

    assert 'unauthorized tables' in result['error']
    service.execute_sql.assert_not_called()
    trigger.assert_called_once()


@patch.object(llm_module, 'trigger_log_error')
@patch.object(llm_module, 'end_log')
@patch.object(llm_module, 'start_log', return_value=SimpleNamespace(id=1))
def test_execute_query_cte_alias_does_not_bypass_whitelist(_start, _end, _trigger):
    service = _service()
    service.execute_sql = MagicMock()
    sql = 'WITH orders AS (SELECT * FROM sys_user) SELECT * FROM orders'

    result = service.execute_analysis_query(MagicMock(), {'purpose': 'x', 'sql': sql})

    assert 'sys_user' in result['error']
    service.execute_sql.assert_not_called()


@patch.object(llm_module, 'trigger_log_error')
@patch.object(llm_module, 'end_log')
@patch.object(llm_module, 'start_log', return_value=SimpleNamespace(id=1))
def test_execute_query_returns_rows_for_allowed_table(_start, end, trigger):
    service = _service()
    service.execute_sql = MagicMock(return_value={'fields': ['n'], 'data': [{'n': 3}]})
    sql = 'WITH t AS (SELECT * FROM orders) SELECT count(*) AS n FROM t'

    result = service.execute_analysis_query(MagicMock(), {'purpose': '订单数', 'sql': sql})

    assert result == {'purpose': '订单数', 'sql': sql, 'data': [{'n': 3}]}
    service.execute_sql.assert_called_once_with(sql=sql)
    trigger.assert_not_called()
    assert end.call_args.kwargs['full_message']['count'] == 1


@patch.object(llm_module, 'trigger_log_error')
@patch.object(llm_module, 'end_log')
@patch.object(llm_module, 'start_log', return_value=SimpleNamespace(id=1))
def test_execute_query_reports_read_only_rejection(_start, _end, trigger):
    service = _service()
    service.execute_sql = MagicMock(side_effect=ValueError('SQL can only contain read operations'))

    result = service.execute_analysis_query(MagicMock(), {'purpose': 'x', 'sql': 'DELETE FROM orders'})

    assert 'read operations' in result['error']
    trigger.assert_called_once()


@patch.object(llm_module, 'trigger_log_error')
@patch.object(llm_module, 'end_log')
@patch.object(llm_module, 'start_log', return_value=SimpleNamespace(id=1))
def test_execute_query_error_hides_traceback(_start, end, _trigger):
    service = _service()
    traceback_text = ('Traceback (most recent call last):\n  File "/home/u/backend/apps/db/db.py", line 9\n'
                      'ValueError: SQL can only contain read operations')
    service.execute_sql = MagicMock(side_effect=llm_module.SQLBotDBError(traceback_text))

    result = service.execute_analysis_query(MagicMock(), {'purpose': 'x', 'sql': 'SELECT 1 FROM orders'})

    assert result['error'] == 'ValueError: SQL can only contain read operations'
    assert '/home/' not in end.call_args.kwargs['full_message']['error']


# ---------- run_analysis_supplementary_queries: skip paths ----------

def _supplementary_service(user_id=2, assistant=None, out_ds=None):
    service = _service()
    service.current_user = SimpleNamespace(id=user_id)
    service.current_assistant = assistant
    service.out_ds_instance = out_ds
    service.chat_question = ChatQuestion(chat_id=1, question='q')
    service.generate_analysis_plan = MagicMock(return_value=_plan({'purpose': 'p', 'sql': 'SELECT 1 FROM orders'}))
    service.execute_analysis_query = MagicMock(return_value={'purpose': 'p', 'data': []})
    return service


def _plan_question():
    return ChatQuestion(chat_id=1, question='q')


@patch.object(llm_module, 'get_table_schema', return_value=('schema', ['orders']))
@patch.object(llm_module, 'get_row_permission_filters', return_value=[{'table': 'orders', 'filter': 'x'}])
def test_supplementary_skipped_when_row_permission_applies(_filters, _schema):
    service = _supplementary_service()

    assert service.run_analysis_supplementary_queries(MagicMock(), ['orders'], _plan_question()) == []
    service.generate_analysis_plan.assert_not_called()


@patch.object(llm_module, 'get_table_schema', return_value=('schema', ['orders']))
@patch.object(llm_module, 'get_row_permission_filters', return_value=[])
def test_supplementary_skipped_for_dynamic_datasource(_filters, _schema):
    service = _supplementary_service(out_ds=object())

    assert service.run_analysis_supplementary_queries(MagicMock(), ['orders'], _plan_question()) == []
    assert service.start_analysis_supplementary_queries(['orders'], [], []) is None
    service.generate_analysis_plan.assert_not_called()


@patch.object(llm_module, 'get_table_schema', return_value=('schema', ['orders']))
@patch.object(llm_module, 'get_row_permission_filters', return_value=[])
def test_supplementary_runs_planned_queries(_filters, _schema):
    service = _supplementary_service()
    plan_question = _plan_question()

    results = service.run_analysis_supplementary_queries(MagicMock(), ['orders'], plan_question)

    assert results == [{'purpose': 'p', 'data': []}]
    service.execute_analysis_query.assert_called_once()
    assert plan_question.analysis_schema == 'schema'
    # 规划只写自己的快照，不改共享的 chat_question
    assert service.chat_question.analysis_schema == ''


@patch.object(llm_module, 'get_table_schema', return_value=('schema', ['orders']))
@patch.object(llm_module, 'get_row_permission_filters', return_value=[])
def test_supplementary_plan_failure_degrades_to_empty(_filters, _schema):
    service = _supplementary_service()
    service.generate_analysis_plan = MagicMock(side_effect=RuntimeError('llm down'))

    assert service.run_analysis_supplementary_queries(MagicMock(), ['orders'], _plan_question()) == []
    service.execute_analysis_query.assert_not_called()


@patch.object(llm_module.settings, 'ANALYSIS_SUPPLEMENTARY_QUERY_MAX', 0)
def test_supplementary_disabled_by_setting():
    service = _supplementary_service()

    assert service.run_analysis_supplementary_queries(MagicMock(), ['orders'], _plan_question()) == []
    assert service.start_analysis_supplementary_queries(['orders'], [], []) is None
    service.generate_analysis_plan.assert_not_called()


# ---------- parallel planning ----------

def test_start_supplementary_runs_in_background_with_snapshot():
    service = _supplementary_service()
    started = threading.Event()
    release = threading.Event()
    seen = {}

    def fake_run(tables, plan_question):
        started.set()
        release.wait(5)
        seen['tables'] = tables
        seen['data'] = plan_question.data
        seen['fields'] = plan_question.fields
        seen['row_count'] = plan_question.data_row_count
        return [{'purpose': 'p', 'data': [{'n': 1}]}]

    service._run_analysis_supplementary_queries_in_session = fake_run
    rows = [{'a': i} for i in range(3)]

    future = service.start_analysis_supplementary_queries(['orders'], ['a'], rows)
    assert started.wait(5)
    # 后台规划进行时，主线程（图表生成）修改共享的 chat_question 不影响快照
    service.chat_question.data = 'changed by chart'
    service.chat_question.fields = 'changed by chart'
    assert not future.done()
    release.set()

    assert LLMService.collect_analysis_supplementary_results(future) == [{'purpose': 'p', 'data': [{'n': 1}]}]
    assert seen['tables'] == ['orders']
    assert orjson.loads(seen['data']) == rows
    assert orjson.loads(seen['fields']) == ['a']
    assert seen['row_count'] == 3


@patch.object(llm_module.settings, 'ANALYSIS_PLAN_DATA_ROWS', 2)
def test_start_supplementary_limits_rows_for_planning():
    service = _supplementary_service()
    seen = {}
    service._run_analysis_supplementary_queries_in_session = lambda tables, q: seen.update(
        data=q.data, row_count=q.data_row_count) or []

    future = service.start_analysis_supplementary_queries(['orders'], [], [{'a': i} for i in range(5)])
    LLMService.collect_analysis_supplementary_results(future)

    assert len(orjson.loads(seen['data'])) == 2
    assert seen['row_count'] == 5


def test_collect_supplementary_degrades_on_failure_and_timeout():
    assert LLMService.collect_analysis_supplementary_results(None) == []

    failed = Future()
    failed.set_exception(RuntimeError('boom'))
    assert LLMService.collect_analysis_supplementary_results(failed) == []

    with patch.object(llm_module.settings, 'ANALYSIS_SUPPLEMENTARY_TIMEOUT', 0.01):
        assert LLMService.collect_analysis_supplementary_results(Future()) == []


def test_run_task_starts_planning_before_chart_generation():
    source = _read('backend/apps/chat/task/llm.py')
    run_task = source[source.index('    def run_task('):source.index('    def run_recommend_questions_task_async')]

    start = run_task.index('self.start_analysis_supplementary_queries(')
    chart = run_task.index('self.generate_chart(')
    collect = run_task.index('self.collect_analysis_supplementary_results(')
    assert start < chart < collect
    assert 'analysis_future.cancel()' in run_task


def test_new_operations_have_distinct_values():
    values = [op.value for op in OperationEnum]
    assert len(values) == len(set(values))
    # '15' is upstream's COMPLETE_QUESTION; auto analysis uses the next codes.
    assert OperationEnum.ANALYSIS_PLAN.value == '16'
    assert OperationEnum.ANALYSIS_QUERY.value == '17'


# ---------- frontend contract ----------

def _read(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding='utf-8') as f:
        return f.read()


def test_frontend_removes_analysis_button_and_renders_inline_analysis():
    index_vue = _read('frontend/src/views/chat/index.vue')
    chart_answer = _read('frontend/src/views/chat/answer/ChartAnswer.vue')

    assert 'clickAnalysis(' not in index_vue
    assert "t('chat.data_analysis')" not in index_vue
    assert "case 'analysis-result':" in chart_answer
    assert "case 'analysis-error':" in chart_answer
    assert '<MdComponent' in chart_answer and 'v-html' not in chart_answer


def test_frontend_log_labels_exist_in_all_locales():
    for lang in ('zh-CN', 'zh-TW', 'en', 'ko-KR', 'th-TH'):
        data = orjson.loads(_read(f'frontend/src/i18n/{lang}.json'))
        assert data['chat']['log']['ANALYSIS_PLAN'], lang
        assert data['chat']['log']['ANALYSIS_QUERY'], lang
        backend = orjson.loads(_read(f'backend/locales/{lang}.json'))
        assert '{msg}' in backend['i18n_chat']['analysis_failed'], lang
