import base64
import hashlib
import inspect
import json
import logging
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re
from urllib.parse import urlparse

from fastapi import Request
from common.core.config import settings
from typing import Optional

import jwt
import orjson
from jwt.exceptions import InvalidTokenError

from common.core import security


def generate_password_reset_token(email: str) -> str:
    delta = timedelta(hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
    now = datetime.now(timezone.utc)
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": email},
        settings.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )
    return encoded_jwt


def verify_password_reset_token(token: str) -> str | None:
    try:
        decoded_token = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        return str(decoded_token["sub"])
    except InvalidTokenError:
        return None


def deepcopy_ignore_extra(src, dest):
    import copy
    for attr in vars(src):
        if hasattr(dest, attr):
            src_value = getattr(src, attr)
            dest_value = copy.deepcopy(src_value)  # deep copy
            setattr(dest, attr, dest_value)
    return dest


def extract_nested_json(text):
    stack = []
    start_index = -1
    results = []

    for i, char in enumerate(text):
        if char in '{[':
            if not stack:  # 记录起始位置
                start_index = i
            stack.append(char)
        elif char in '}]':
            if stack and ((char == '}' and stack[-1] == '{') or (char == ']' and stack[-1] == '[')):
                stack.pop()
                if not stack:  # 栈空时截取完整JSON
                    json_str = text[start_index:i + 1]
                    try:
                        orjson.loads(json_str)  # 验证有效性
                        results.append(json_str)
                    except:
                        pass
            else:
                stack = []  # 括号不匹配则重置
    if len(results) > 0 and results[0]:
        return results[0]
    return None

def string_to_numeric_hash(text: str, bits: Optional[int] = 64) -> int:
    hash_bytes = hashlib.sha256(text.encode()).digest()
    hash_num = int.from_bytes(hash_bytes, byteorder='big')
    max_bigint = 2**63 - 1
    return hash_num % max_bigint


def setup_logging():
    # 确保日志目录存在
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 日志格式
    formatter = logging.Formatter(
        f'{settings.LOG_FORMAT}'
    )
    
    # 控制台日志
    console_handler = logging.StreamHandler()
    console_handler.setLevel(settings.LOG_LEVEL)
    console_handler.setFormatter(formatter)
    
    # 文件日志处理器
    file_handlers = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warn': logging.WARNING,
        'error': logging.ERROR
    }
    
    # 主日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # 设置最低级别
    
    # 添加控制台处理器
    root_logger.addHandler(console_handler)
    
    # 为每个级别创建文件处理器
    for level_name, level in file_handlers.items():
        file_path = log_dir / f"{level_name}.log"
        handler = RotatingFileHandler(
            file_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        handler.setLevel(level)
        handler.setFormatter(formatter)
        
        # 添加过滤器只处理特定级别日志
        if level_name == 'debug':
            handler.addFilter(lambda record: record.levelno == logging.DEBUG)
        elif level_name == 'info':
            handler.addFilter(lambda record: record.levelno == logging.INFO)
        elif level_name == 'warn':
            handler.addFilter(lambda record: record.levelno == logging.WARNING)
        elif level_name == 'error':
            handler.addFilter(lambda record: record.levelno >= logging.ERROR)
        
        root_logger.addHandler(handler)
    
    # SQL日志特殊处理
    if settings.LOG_LEVEL == "DEBUG" and settings.SQL_DEBUG:
        sql_logger = logging.getLogger('sqlalchemy.engine')
        sql_logger.setLevel(logging.DEBUG)
        
        sql_handler = RotatingFileHandler(
            log_dir / "sql.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=2,
            encoding='utf-8'
        )
        sql_handler.setFormatter(formatter)
        sql_logger.addHandler(sql_handler)
        
setup_logging()


class CallerLogger(logging.Logger):
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        super().__init__(logger.name, logger.level)

    def _log(self, level, msg, args, exc_info=None, extra=None, stacklevel=3):
        if self.logger.isEnabledFor(level):
            self.logger._log(level, msg, args, exc_info=exc_info, extra=extra, stacklevel=stacklevel)

class SQLBotLogUtil:
    
    @staticmethod
    def _get_logger() -> logging.Logger:
        frame = inspect.currentframe()
        try:
            caller_frame = frame.f_back.f_back
            module_name = caller_frame.f_globals.get('__name__', '__main__')
            return CallerLogger(logging.getLogger(module_name))
        finally:
            del frame
        

    @staticmethod
    def debug(msg: str, *args, **kwargs):
        logger = SQLBotLogUtil._get_logger()
        if logger.isEnabledFor(logging.DEBUG):
            logger._log(logging.DEBUG, msg, args, **kwargs)

    @staticmethod
    def info(msg: str, *args, **kwargs):
        logger = SQLBotLogUtil._get_logger()
        if logger.isEnabledFor(logging.INFO):
            logger._log(logging.INFO, msg, args, **kwargs)

    @staticmethod
    def warning(msg: str, *args, **kwargs):
        logger = SQLBotLogUtil._get_logger()
        if logger.isEnabledFor(logging.WARNING):
            logger._log(logging.WARNING, msg, args, **kwargs)

    @staticmethod
    def error(msg: str, *args, exc_info: Optional[bool] = None, **kwargs):
        logger = SQLBotLogUtil._get_logger()
        if logger.isEnabledFor(logging.ERROR):
            logger._log(
                logging.ERROR, 
                msg, 
                args, 
                exc_info=exc_info if exc_info is not None else True,
                **kwargs
            )

    @staticmethod
    def exception(msg: str, *args, **kwargs):
        logger = SQLBotLogUtil._get_logger()
        if logger.isEnabledFor(logging.ERROR):
            logger._log(logging.ERROR, msg, args, exc_info=True, **kwargs)

    @staticmethod
    def critical(msg: str, *args, **kwargs):
        logger = SQLBotLogUtil._get_logger()
        if logger.isEnabledFor(logging.CRITICAL):
            logger._log(logging.CRITICAL, msg, args, **kwargs)
            
def prepare_for_orjson(data):
    if not data:
        return data
    if isinstance(data, bytes):
        return base64.b64encode(data).decode('utf-8')
    elif isinstance(data, dict):
        return {k: prepare_for_orjson(v) for k, v in data.items()}
    elif isinstance(data, (list, tuple)):
        return [prepare_for_orjson(item) for item in data]
    else:
        return data
        
    
def prepare_model_arg(origin_arg: str):
    if not isinstance(origin_arg, str):
        return origin_arg
    if not origin_arg.strip()[0] in {'{', '['}:
        return origin_arg
    try:
        return json.loads(origin_arg)
    except:
        return origin_arg
    
def get_origin_from_referer(request: Request):
    referer = request.headers.get("referer")
    if not referer:
        return None
    
    try:
        parsed = urlparse(referer)
        if not parsed.scheme or not parsed.hostname:
            return None
        port = parsed.port
        if port:
            if (parsed.scheme == "http" and port != 80) or \
               (parsed.scheme == "https" and port != 443):
                return f"{parsed.scheme}://{parsed.hostname}:{port}"
        
        return f"{parsed.scheme}://{parsed.hostname}"
    except Exception as e:
        SQLBotLogUtil.error(f"解析 Referer 出错: {e}")
        return referer

def origin_match_domain(origin: str, domain: str) -> bool:
    if not origin or not domain:
        return False
    origin_normalized = origin.rstrip('/')
    
    for d in re.split(r'[,;]', domain):
        if d.strip().rstrip('/') == origin_normalized:
            return True
    
    return False

def get_domain_list(domain: str) -> list[str]:
    domains = []
    if not domain:
        return domains
    for d in re.split(r'[,;]', domain):
        d_clean = d.strip().rstrip('/')
        if d_clean:
            domains.append(d_clean)
    return domains
    

def equals_ignore_case(str1: str, *args: str) -> bool:
    if str1 is None:
        return None in args
    for arg in args:
        if arg is None:
            continue
        if str1.casefold() == arg.casefold():
            return True
    return False