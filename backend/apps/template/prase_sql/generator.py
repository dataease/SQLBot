from typing import Union

from apps.db.constant import DB
from apps.template.template import get_base_template, get_sql_template as get_base_sql_template


def get_prase_sql_template():
    template = get_base_template()
    return template['template']['prase_sql']

