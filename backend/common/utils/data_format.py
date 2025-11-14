import pandas as pd

class DataFormat:
    @staticmethod
    def safe_convert_to_string(df):
        df_copy = df.copy()

        def format_value(x):
            if pd.isna(x):
                return ""

            return "\u200b" + str(x)

        for col in df_copy.columns:
            df_copy[col] = df_copy[col].apply(format_value)

        return df_copy

    @staticmethod
    def convert_large_numbers_in_object_array(obj_array, int_threshold=1e15, float_threshold=1e10):
        """处理对象数组，将每个对象中的大数字转换为字符串"""

        def format_float_without_scientific(value):
            """格式化浮点数，避免科学记数法"""
            if value == 0:
                return "0"
            formatted = f"{value:.15f}"
            if '.' in formatted:
                formatted = formatted.rstrip('0').rstrip('.')
            return formatted

        def process_object(obj):
            """处理单个对象"""
            if not isinstance(obj, dict):
                return obj

            processed_obj = {}
            for key, value in obj.items():
                if isinstance(value, (int, float)):
                    # 只转换大数字
                    if isinstance(value, int) and abs(value) >= int_threshold:
                        processed_obj[key] = str(value)
                    elif isinstance(value, float) and (abs(value) >= float_threshold or abs(value) < 1e-6):
                        processed_obj[key] = format_float_without_scientific(value)
                    else:
                        processed_obj[key] = value
                elif isinstance(value, dict):
                    # 处理嵌套对象
                    processed_obj[key] = process_object(value)
                elif isinstance(value, list):
                    # 处理对象中的数组
                    processed_obj[key] = [process_item(item) for item in value]
                else:
                    processed_obj[key] = value
            return processed_obj

        def process_item(item):
            """处理数组中的项目"""
            if isinstance(item, dict):
                return process_object(item)
            return item

        return [process_item(obj) for obj in obj_array]

    @staticmethod
    def convert_object_array_for_pandas(column_list: list, data_list: list):
        _fields_list = []
        for field_idx, field in enumerate(column_list):
            _fields_list.append(field.name)

        md_data = []
        for inner_data in data_list:
            _row = []
            for field_idx, field in enumerate(column_list):
                value = inner_data.get(field.value)
                _row.append(value)
            md_data.append(_row)
        return md_data, _fields_list

    @staticmethod
    def format_pd_data(column_list: list, data_list: list, col_formats: dict = None):
        # 预处理数据并记录每列的格式类型
        # 格式类型：'text'（文本）、'number'（数字）、'default'（默认）
        _fields_list = []

        if col_formats is None:
            col_formats = {}
        for field_idx, field in enumerate(column_list):
            _fields_list.append(field.name)
            col_formats[field_idx] = 'default'  # 默认不特殊处理

        data = []

        for _data in data_list:
            _row = []
            for field_idx, field in enumerate(column_list):
                value = _data.get(field.value)
                if value is not None:
                    # 检查是否为数字且需要特殊处理
                    if isinstance(value, (int, float)):
                        # 整数且超过15位 → 转字符串并标记为文本列
                        if isinstance(value, int) and len(str(abs(value))) > 15:
                            value = str(value)
                            col_formats[field_idx] = 'text'
                        # 小数且超过15位有效数字 → 转字符串并标记为文本列
                        elif isinstance(value, float):
                            decimal_str = format(value, '.16f').rstrip('0').rstrip('.')
                            if len(decimal_str) > 15:
                                value = str(value)
                                col_formats[field_idx] = 'text'
                        # 其他数字列标记为数字格式（避免科学记数法）
                        elif col_formats[field_idx] != 'text':
                            col_formats[field_idx] = 'number'
                _row.append(value)
            data.append(_row)

        return data, _fields_list, col_formats