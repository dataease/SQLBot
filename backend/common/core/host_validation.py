import re

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# 合法 Host：域名 / IPv4 / IPv6（含端口），排除 '/'、'@'、空白等非法字符。
# Starlette 的 URL(scope) 会把 Host 头原始值拼进 URL，Host 携带路径片段会污染
# request.url.path 等派生属性（历史上被用于绕过认证白名单），因此请求入口处直接拒绝。
_HOST_RE = re.compile(r'^[A-Za-z0-9.\-:\[\]]{1,255}$')


class HostValidationMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request, call_next):
        host = request.headers.get("host")
        if not host or not _HOST_RE.match(host):
            return JSONResponse(
                {"code": 400, "data": None, "msg": "invalid host header"},
                status_code=400,
            )
        return await call_next(request)
