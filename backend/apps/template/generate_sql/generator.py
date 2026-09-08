from typing import Union

from apps.db.constant import DB
from apps.template.template import get_base_template, get_sql_template as get_base_sql_template
from common.core.config import settings


def get_sql_template():
    template = get_base_template()
    sql_template = template['template']['sql']
    if not settings.TABLE_SAMPLE_DATA_ENABLED:
        # Do not mutate shared templates or render pre-existing sample values.
        sql_template = sql_template.copy()
        sql_template['generate_basic_info'] = sql_template['generate_basic_info'].replace('{sample_data}', '')
    return sql_template


def get_sql_example_template(db_type: Union[str, DB]):
    template = get_base_sql_template(db_type)
    return template['template']
