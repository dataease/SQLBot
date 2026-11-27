import json

import pandas as pd
import pytest

from apps.datasource.utils.excel import parse_excel_preview, read_import_dataframe


@pytest.fixture(params=["csv", "CSV", "CsV"])
def stored_csv(tmp_path, request):
    path = tmp_path / f"sales_0123456789.{request.param}"
    path.write_text("region,units\nEast,3\nWest,7\n", encoding="utf-8")
    return str(path)


def test_preview_csv_with_any_extension_case(stored_csv):
    [sheet] = parse_excel_preview(stored_csv)
    assert sheet["sheetName"] == "Sheet1"
    assert sheet["rows"] == 2
    assert sheet["data"] == [
        {"region": "East", "units": 3},
        {"region": "West", "units": 7},
    ]


def test_csv_preview_is_json_serializable_with_infinite_values(tmp_path):
    path = tmp_path / "measurements.csv"
    path.write_text(
        "row,reading,label\n1,inf,upper\n2,-Inf,lower\n3,,missing\n4,1.5,finite\n5,2.0,extra\n",
        encoding="utf-8",
    )

    [sheet] = parse_excel_preview(str(path), max_rows=4)
    assert sheet["rows"] == 5
    assert sheet["fields"][1] == {"fieldName": "reading", "fieldType": "float"}
    preview = json.loads(json.dumps(sheet["data"], allow_nan=False))
    assert [row["reading"] for row in preview] == ["Infinity", "-Infinity", None, 1.5]


def test_import_stored_csv_with_any_extension_case(stored_csv):
    frame = read_import_dataframe(
        stored_csv, "Sheet1", {"region": "string", "units": "int"}
    )
    assert frame["region"].tolist() == ["East", "West"]
    assert frame["units"].tolist() == [3, 7]


def test_csv_import_keeps_literal_values_in_explicit_text_columns(tmp_path):
    path = tmp_path / "regions.csv"
    path.write_text(
        "region,code,units,price,created\n"
        "NA,NULL,NA,NA,NA\n"
        "N/A,001,2.5,1.25,2026-11-16\n"
        ",NaN,7,2.5,\n"
        '" NA ",,9,3.5,2026-11-17\n',
        encoding="utf-8",
    )

    frame = read_import_dataframe(
        str(path),
        "Sheet1",
        {
            "region": "string",
            "code": "string",
            "units": "int",
            "price": "float",
            "created": "datetime",
        },
    )

    pd.testing.assert_series_equal(
        frame["region"],
        pd.Series(["NA", "N/A", pd.NA, " NA "], dtype="string", name="region"),
    )
    pd.testing.assert_series_equal(
        frame["code"],
        pd.Series(["NULL", "001", "NaN", pd.NA], dtype="string", name="code"),
    )
    assert frame["units"].tolist() == [pd.NA, 3, 7, 9]
    assert pd.isna(frame.loc[0, "price"])
    assert frame.loc[1, "price"] == 1.25
    assert pd.isna(frame.loc[0, "created"])
    assert frame.loc[1, "created"] == pd.Timestamp("2026-11-16")


def test_excel_reader_preserves_named_sheet(tmp_path):
    path = tmp_path / "sales.CSV.xlsx"
    pd.DataFrame({"units": [3]}).to_excel(path, sheet_name="Sales", index=False)

    [sheet] = parse_excel_preview(str(path))
    assert sheet["sheetName"] == "Sales"
    frame = read_import_dataframe(str(path), "Sales", {"units": "int"})
    assert frame["units"].tolist() == [3]


def test_excel_import_keeps_literal_values_in_explicit_text_columns(tmp_path):
    path = tmp_path / "regions.xlsx"
    pd.DataFrame(
        {
            "region": ["NA", "EU", None, "APAC"],
            "code": ["NULL", "001", "NaN", None],
            "units": ["NA", 2.5, None, 9],
            "price": ["NA", 1.25, None, 3.5],
            "created": ["NA", "2026-11-16", None, "2026-11-17"],
            "inferred": ["NA", 1, None, 2],
        }
    ).to_excel(path, sheet_name="Sales", engine="openpyxl", index=False)

    frame = read_import_dataframe(
        str(path),
        "Sales",
        {
            "region": "string",
            "code": "string",
            "units": "int",
            "price": "float",
            "created": "datetime",
        },
    )

    pd.testing.assert_series_equal(
        frame["region"],
        pd.Series(["NA", "EU", pd.NA, "APAC"], dtype="string", name="region"),
    )
    pd.testing.assert_series_equal(
        frame["code"],
        pd.Series(["NULL", "001", "NaN", pd.NA], dtype="string", name="code"),
    )
    assert frame["units"].tolist() == [pd.NA, 3, pd.NA, 9]
    assert frame["price"].isna().tolist() == [True, False, True, False]
    assert frame.loc[1, "price"] == 1.25
    assert frame["created"].isna().tolist() == [True, False, True, False]
    assert frame.loc[1, "created"] == pd.Timestamp("2026-11-16")
    assert frame["inferred"].isna().tolist() == [True, False, True, False]


@pytest.mark.parametrize("extension", ["csv", "xlsx"])
def test_preview_empty_cells_are_json_null(tmp_path, extension):
    path = tmp_path / f"empty_cells.{extension}"
    frame = pd.DataFrame({
        "row": [1, 2, 3],
        "price": [1.5, None, 0.0],
        "label": [None, "present", "last"],
        "empty": [None, None, None],
    })
    if extension == "csv":
        frame.to_csv(path, index=False)
    else:
        frame.to_excel(path, index=False, engine="openpyxl")

    [sheet] = parse_excel_preview(str(path))
    result = json.loads(json.dumps(sheet, allow_nan=False))
    assert result["rows"] == 3
    assert result["fields"][1] == {"fieldName": "price", "fieldType": "float"}
    assert result["data"] == [
        {"row": 1, "price": 1.5, "label": None, "empty": None},
        {"row": 2, "price": None, "label": "present", "empty": None},
        {"row": 3, "price": 0.0, "label": "last", "empty": None},
    ]
