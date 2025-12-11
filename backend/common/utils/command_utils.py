import re
from typing import Optional, Tuple

from apps.chat.models.chat_model import QuickCommand


def parse_quick_command(input_str: str) -> Tuple[Optional[QuickCommand], str, Optional[int], Optional[str]]:
    """
    解析字符串中的快速命令

    Args:
        input_str: 输入字符串

    Returns:
        Tuple[Optional[QuickCommand], str, Optional[int], Optional[str]]:
        (命令枚举, 去除命令的字符串, 数字参数, 警告信息)
        如果解析成功: (命令, 文本, 数字, None)
        如果解析失败: (None, 原字符串, None, 警告信息)
    """

    # 获取所有命令值
    command_values = [cmd.value for cmd in QuickCommand]

    # 1. 检查字符串中是否包含任何命令
    found_commands = []
    for cmd_value in command_values:
        # 使用正则表达式查找独立的命令（前后是单词边界或空格）
        pattern = r'(?<!\S)' + re.escape(cmd_value) + r'(?!\S)'
        if re.search(pattern, input_str):
            found_commands.append(cmd_value)

    # 如果没有找到任何命令，直接返回原字符串
    if not found_commands:
        return None, input_str, None, None

    # 2. 检查是否包含多个命令
    if len(found_commands) > 1:
        return None, input_str, None, f"错误: 字符串中包含多个命令: {', '.join(found_commands)}"

    # 此时只有一个命令
    command_str = found_commands[0]

    # 3. 构建完整匹配模式，匹配命令及其后的可选数字
    # 模式: 命令 + 可选的空格 + 可选的数字
    full_pattern = r'(?<!\S)(' + re.escape(command_str) + r')(?:\s+(\d+))?(?!\S)'
    match = re.search(full_pattern, input_str)

    if not match:
        return None, input_str, None, f"错误: 命令格式不正确"

    command_part = match.group(1)
    number_part = match.group(2)

    # 4. 检查命令是否在字符串末尾
    # 计算命令的结束位置
    command_end_pos = match.end()

    # 如果命令不在字符串的末尾（忽略尾部空格）
    if command_end_pos < len(input_str.rstrip()):
        # 检查命令后面是否有非空格字符
        remaining_text = input_str[command_end_pos:].strip()
        if remaining_text:
            return None, input_str, None, f"错误: 命令不在字符串末尾，命令后还有内容: '{remaining_text}'"

    # 5. 检查命令前面是否有内容，但中间没有空格
    # 找到命令前面的部分
    before_command = input_str[:match.start()]

    # 如果命令前面有内容，检查是否有空格分隔
    if before_command and not before_command.endswith(' '):
        # 检查命令是否在字符串开头
        if match.start() > 0:
            return None, input_str, None, f"错误: 命令与前面的文本没有用空格分隔"

    # 6. 获取命令枚举
    command = None
    for cmd in QuickCommand:
        if cmd.value == command_part:
            command = cmd
            break

    if not command:
        return None, input_str, None, f"错误: 未识别的命令: {command_part}"

    # 7. 提取去除命令和数字后的文本
    # 获取命令前的文本
    text_before_command = input_str[:match.start()].rstrip()

    # 8. 处理数字参数
    record_id = None
    if number_part:
        try:
            record_id = int(number_part)
        except ValueError:
            return None, input_str, None, f"错误: 数字参数格式不正确: {number_part}"

    return command, text_before_command, record_id, None


