from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import pandas as pd

FIELD_TYPE_MAP = {
    'int64': 'int',
    'int32': 'int',
    'float64': 'float',
    'float32': 'float',
    'datetime64': 'datetime',
    'datetime64[ns]': 'datetime',
    'object': 'string',
    'string': 'string',
    'bool': 'string',
}

USER_TYPE_TO_PANDAS = {
    'int': 'int64',
    'float': 'float64',
    'datetime': 'datetime64[ns]',
    'string': 'string',
}


def infer_field_type(dtype) -> str:
    dtype_str = str(dtype)
    return FIELD_TYPE_MAP.get(dtype_str, 'string')


def _round_import_integer(value):
    """Round explicitly selected integer values without a float intermediate."""
    if pd.isna(value) or (isinstance(value, str) and not value.strip()):
        return pd.NA
    if isinstance(value, bool):
        return int(value)
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('Invalid numeric value for integer field') from exc
    if not number.is_finite():
        raise ValueError('Integer fields require finite numeric values')
    rounded = number.to_integral_value(rounding=ROUND_HALF_UP)
    if rounded < -(2 ** 63) or rounded > 2 ** 63 - 1:
        raise ValueError('Rounded value is outside the signed 64-bit integer range')
    return int(rounded)


def read_import_dataframe(save_path: str, sheet_name: str, field_mapping: dict):
    """Read stored cell values; round only columns explicitly selected as integers."""
    dtype_dict = {
        column: 'object' if field_type == 'int' else USER_TYPE_TO_PANDAS.get(field_type, 'string')
        for column, field_type in field_mapping.items()
    }
    if save_path.endswith('.csv'):
        df = pd.read_csv(save_path, engine='c', dtype=dtype_dict)
    else:
        df = pd.read_excel(save_path, sheet_name=sheet_name, engine='calamine', dtype=dtype_dict)
    for column, field_type in field_mapping.items():
        if field_type == 'int' and column in df.columns:
            try:
                # Build a nullable integer array directly: Series.map can coerce
                # large integers plus missing values to lossy float64 values.
                df[column] = pd.array([_round_import_integer(value) for value in df[column]], dtype='Int64')
            except ValueError as exc:
                raise ValueError(f"Column '{column}': {exc}") from exc
    return df


def parse_excel_preview(save_path: str, max_rows: int = 10):
    sheets_data = []
    if save_path.endswith(".csv"):
        df = pd.read_csv(save_path, engine='c')
        fields = []
        for col in df.columns:
            fields.append({
                "fieldName": col,
                "fieldType": infer_field_type(df[col].dtype)
            })
        preview_df = df.head(max_rows).replace({pd.NA: None, float('nan'): None})
        preview_data = preview_df.to_dict(orient='records')
        sheets_data.append({
            "sheetName": "Sheet1",
            "fields": fields,
            "data": preview_data,
            "rows": len(df)
        })
    else:
        sheet_names = pd.ExcelFile(save_path).sheet_names
        for sheet_name in sheet_names:
            df = pd.read_excel(save_path, sheet_name=sheet_name, engine='calamine')
            fields = []
            for col in df.columns:
                fields.append({
                    "fieldName": col,
                    "fieldType": infer_field_type(df[col].dtype)
                })
            preview_df = df.head(max_rows).replace({pd.NA: None, float('nan'): None})
            preview_data = preview_df.to_dict(orient='records')
            sheets_data.append({
                "sheetName": sheet_name,
                "fields": fields,
                "data": preview_data,
                "rows": len(df)
            })
    return sheets_data
