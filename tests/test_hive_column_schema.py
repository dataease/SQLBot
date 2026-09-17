"""Regression tests for Hive DESCRIBE result handling."""

import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))


class HiveColumnSchemaTestCase(unittest.TestCase):
    def test_ignores_driver_specific_describe_metadata(self) -> None:
        from apps.datasource.models.datasource import ColumnSchema

        row = (
            "customer_id",
            "bigint",
            "customer identifier",
            "PRIMARY_KEY",
            "",
            "",
        )

        field = ColumnSchema(*row)

        self.assertEqual("customer_id", field.fieldName)
        self.assertEqual("bigint", field.fieldType)
        self.assertEqual("customer identifier", field.fieldComment)


if __name__ == "__main__":
    unittest.main()
