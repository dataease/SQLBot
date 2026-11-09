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


def test_import_stored_csv_with_any_extension_case(stored_csv):
    frame = read_import_dataframe(
        stored_csv, "Sheet1", {"region": "string", "units": "int"}
    )
    assert frame["region"].tolist() == ["East", "West"]
    assert frame["units"].tolist() == [3, 7]


def test_excel_reader_preserves_named_sheet(tmp_path):
    path = tmp_path / "sales.CSV.xlsx"
    pd.DataFrame({"units": [3]}).to_excel(path, sheet_name="Sales", index=False)

    [sheet] = parse_excel_preview(str(path))
    assert sheet["sheetName"] == "Sales"
    frame = read_import_dataframe(str(path), "Sales", {"units": "int"})
    assert frame["units"].tolist() == [3]
