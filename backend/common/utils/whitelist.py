# app/utils/whitelist.py
import re
from typing import List, Pattern
from common.core.config import settings
from common.utils.utils import SQLBotLogUtil
wlist = [
    "/",
    "/docs",
    "/login/*",
    "*.json",
    "*.ico",
    "*.html",
    "*.js",
    "*.css",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.svg",
    "*.woff",
    "*.woff2",
    "*.ttf",
    "*.eot",
    "*.otf",
    "/mcp*",
    "/system/license",
    "/system/config/key",
    "/images/*",
    "/sse",
    "/system/appearance/ui",
    "/system/appearance/picture/*",
    "/system/assistant/validator*",
    "/system/assistant/info/*",
    "/system/assistant/app/*",
    "/system/assistant/picture/*",
    "/system/authentication/platform/status",
    "/system/authentication/login/*",
    "/system/authentication/sso/*",
    "/system/platform/sso/*",
    "/system/platform/client/*",
    "/system/parameter/login"
]

class WhitelistChecker:
    def __init__(self, paths: List[str] = None):
        self.whitelist = paths or wlist
        self._compiled_patterns: List[Pattern] = []
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        for pattern in self.whitelist:
            if "*" in pattern:
                regex_pattern = (
                    pattern.replace(".", r"\.")
                    .replace("*", ".*")
                )
                if not pattern.startswith("/"):
                    regex_pattern = f"^{regex_pattern}$"
                else:
                    regex_pattern = f"^{regex_pattern}$"
                try:
                    self._compiled_patterns.append(re.compile(regex_pattern))
                except re.error:
                    SQLBotLogUtil.error(f"Invalid regex pattern: {regex_pattern}")
    
    def is_whitelisted(self, path: str) -> bool:
        prefix = settings.API_V1_STR
        if path.startswith(prefix):
            path = path[len(prefix):]
            
        context_prefix = settings.CONTEXT_PATH
        if context_prefix and path.startswith(context_prefix):
            path = path[len(context_prefix):]
        
        if not path:
            path = '/'
        if path in self.whitelist:
            return True
            
        path = path.rstrip('/')
        return any(
            pattern.match(path) is not None 
            for pattern in self._compiled_patterns
        )

    def add_path(self, path: str) -> None:
       
        if path not in self.whitelist:
            self.whitelist.append(path)
            if "*" in path:
                self._compile_patterns()

whiteUtils = WhitelistChecker()