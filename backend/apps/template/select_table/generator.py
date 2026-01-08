from apps.template.template import get_base_template


def get_table_selection_template():
    template = get_base_template()
    return template['template']['table_selection']
