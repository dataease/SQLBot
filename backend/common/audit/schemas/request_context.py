from contextvars import ContextVar

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class RequestContext:
    _current_request: ContextVar[Request] = ContextVar("_current_request")

    @classmethod
    def set_request(cls, request: Request):
        return cls._current_request.set(request)

    @classmethod
    def get_request(cls) -> Request:
        try:
            return cls._current_request.get()
        except LookupError:
            raise RuntimeError(
                "No request context found. "
                "Make sure RequestContextMiddleware is installed."
            )

    @classmethod
    def reset(cls, token):
        cls._current_request.reset(token)


class RequestContextMiddlewareCommon(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 设置请求上下文
        token = RequestContext.set_request(request)
        try:
            response = await call_next(request)
            return response
        finally:
            RequestContext.reset(token)