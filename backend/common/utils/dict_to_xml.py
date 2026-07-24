"""
将 dict/list 转换为 XML 字符串的工具函数，用于替代 dicttoxml 库（GPL 许可证风险）。
仅依赖 Python 标准库。
"""

import xml.etree.ElementTree as ET


def _add_element(parent: ET.Element, key: str, value, item_func=None):
    """递归地将值添加为 XML 子元素。"""
    elem = ET.SubElement(parent, key)

    if isinstance(value, dict):
        for k, v in value.items():
            _add_element(elem, k, v, item_func)
    elif isinstance(value, list):
        item_name = item_func(key) if item_func else 'item'
        for item in value:
            _add_element(elem, item_name, item, item_func)
    elif isinstance(value, bool):
        elem.text = str(value).lower()
    elif value is None:
        elem.text = ''
    else:
        elem.text = str(value)


def dict_to_xml(data: dict | list, root_name: str = 'root', item_func=None) -> str:
    """
    将 dict 或 list 转换为 XML 字符串。

    :param data: 要转换的 dict 或 list
    :param root_name: XML 根元素名称
    :param item_func: 列表项元素名的函数，接收父元素名，返回子元素名
    :return: XML 字符串
    """
    root = ET.Element(root_name)

    if isinstance(data, dict):
        for key, value in data.items():
            _add_element(root, key, value, item_func)
    elif isinstance(data, list):
        item_name = item_func(root_name) if item_func else 'item'
        for item in data:
            _add_element(root, item_name, item, item_func)
    else:
        root.text = str(data)

    return ET.tostring(root, encoding='unicode', xml_declaration=False)
