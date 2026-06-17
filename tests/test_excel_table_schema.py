import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_ROOT = os.path.join(PROJECT_ROOT, "backend")
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from apps.datasource.crud import datasource as datasource_crud  # noqa: E402


def make_table_objs(count: int):
    table_objs = []
    for index in range(count):
        table_name = f"sheet_{index}"
        table = SimpleNamespace(
            id=index + 1,
            table_name=table_name,
            custom_comment="",
            embedding="[1.0, 0.0]",
        )
        field = SimpleNamespace(
            field_name="amount",
            field_type="int",
            custom_comment="",
        )
        table_objs.append(SimpleNamespace(schema="public", table=table, fields=[field]))
    return table_objs


class TestExcelTableSchema(unittest.TestCase):
    def test_excel_schema_keeps_all_tables_when_embedding_enabled(self):
        table_objs = make_table_objs(12)
        ds = SimpleNamespace(type="excel", table_relation=None)

        with (
            patch.object(datasource_crud, "get_table_obj_by_ds", return_value=table_objs),
            patch.object(datasource_crud.settings, "TABLE_EMBEDDING_ENABLED", True),
            patch.object(datasource_crud, "calc_table_embedding") as calc_embedding,
        ):
            schema, table_names = datasource_crud.get_table_schema(
                session=None,
                current_user=None,
                ds=ds,
                question="sum amount for each sheet",
                embedding=True,
            )

        calc_embedding.assert_not_called()
        self.assertEqual(table_names, [f"sheet_{index}" for index in range(12)])
        self.assertIn("# Table: public.sheet_0", schema)
        self.assertIn("# Table: public.sheet_11", schema)

    def test_non_excel_schema_still_uses_table_embedding(self):
        table_objs = make_table_objs(12)
        ds = SimpleNamespace(type="pg", table_relation=None)

        def limited_tables(tables, question):
            return tables[:10]

        with (
            patch.object(datasource_crud, "get_table_obj_by_ds", return_value=table_objs),
            patch.object(datasource_crud.settings, "TABLE_EMBEDDING_ENABLED", True),
            patch.object(
                datasource_crud,
                "calc_table_embedding",
                side_effect=limited_tables,
            ) as calc_embedding,
        ):
            schema, table_names = datasource_crud.get_table_schema(
                session=None,
                current_user=None,
                ds=ds,
                question="sum amount",
                embedding=True,
            )

        calc_embedding.assert_called_once()
        self.assertEqual(table_names, [f"sheet_{index}" for index in range(10)])
        self.assertIn("# Table: public.sheet_0", schema)
        self.assertNotIn("# Table: public.sheet_11", schema)


if __name__ == "__main__":
    unittest.main()
