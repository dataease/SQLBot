"""Offline regression for untrusted persisted Excel identifiers."""
import ast
import re
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / 'apps/datasource/crud/datasource.py'


def validator():
    tree = ast.parse(SOURCE.read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == 'validate_excel_sheet_names')
    scope = {'re': re, 'DatasourceConfigurationError': ValueError}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(SOURCE), 'exec'), scope)
    return scope['validate_excel_sheet_names']


@pytest.mark.parametrize('name', ['x"; SELECT 1; --', 'users', '', None,
                                  'excel_x_0123456789"', 'public.excel_x_0123456789'])
def test_reject_untrusted_table_names(name):
    with pytest.raises(ValueError):
        validator()({'sheets': [{'tableName': name}]})


def test_accept_generated_names():
    names = ['excel_销售_0123456789', 'excel__abcdef0123']
    assert validator()({'sheets': [{'tableName': name} for name in names]}) == names


@pytest.mark.parametrize('sheets', [None, {}, ['bad'], [{}]])
def test_reject_malformed_sheets(sheets):
    with pytest.raises(ValueError):
        validator()({'sheets': sheets})


def test_write_and_delete_validate_and_quote():
    source = SOURCE.read_text()
    assert 'validate_excel_sheet_names(incoming)' in source
    assert 'validate_excel_sheet_names(json.loads(aes_decrypt(term.configuration)))' in source
    assert 'quote_identifier(name)' in source
    assert 'sheet["tableName"]' not in source
