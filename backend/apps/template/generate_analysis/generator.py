from apps.template.template import get_base_template


def get_analysis_template():
    template = get_base_template()
    return template['template']['analysis']


def get_analysis_plan_template():
    template = get_base_template()
    return template['template']['analysis_plan']
