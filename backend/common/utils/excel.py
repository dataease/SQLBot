import pandas as pd

def get_excel_column_count(file_path, sheet_name):
    """获取Excel文件的列数"""
    df_temp = pd.read_excel(
        file_path,
        sheet_name=sheet_name,
        engine='calamine',
        header=0,
        nrows=0
    )
    return len(df_temp.columns)