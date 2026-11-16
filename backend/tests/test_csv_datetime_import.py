"""Regression tests for explicitly selected CSV datetime columns."""

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apps.datasource.utils.excel import read_import_dataframe


class CsvDatetimeImportTests(unittest.TestCase):
    def read_csv(self, contents, mapping):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "import.csv"
            path.write_text(contents, encoding="utf-8")
            return read_import_dataframe(str(path), "Sheet1", mapping)

    def test_dates_and_empty_cells(self):
        result = self.read_csv(
            "created,amount,label\n2026-11-16,1.5,first\n,2.5,second\n",
            {"created": "datetime", "amount": "int", "label": "string"},
        )
        self.assertEqual(str(result["created"].dtype), "datetime64[ns]")
        self.assertEqual(result["created"][0], pd.Timestamp("2026-11-16"))
        self.assertTrue(pd.isna(result["created"][1]))
        self.assertEqual(result["amount"].tolist(), [2, 3])
        self.assertEqual(result["label"].tolist(), ["first", "second"])

    def test_time_components_are_preserved(self):
        result = self.read_csv(
            "created\n2026-11-16 12:34:56\n", {"created": "datetime"}
        )
        self.assertEqual(result["created"][0], pd.Timestamp("2026-11-16 12:34:56"))

    def test_invalid_dates_are_rejected(self):
        with self.assertRaises(ValueError):
            self.read_csv("created\nnot-a-date\n", {"created": "datetime"})

    def test_date_strings_remain_strings_when_selected(self):
        result = self.read_csv("created\n2026-11-16\n", {"created": "string"})
        self.assertEqual(result["created"][0], "2026-11-16")

    def test_empty_csv_with_headers(self):
        result = self.read_csv("created\n", {"created": "datetime"})
        self.assertTrue(result.empty)
        self.assertEqual(str(result["created"].dtype), "datetime64[ns]")


if __name__ == "__main__":
    unittest.main()
