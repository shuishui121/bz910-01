"""统一响应封装与业务异常。

所有接口统一返回 {"code": int, "data": ..., "message": str}。
- 成功: code = 0
- 业务错误: 自定义 BizError.code(如 40901)
- 未捕获异常: code = 50000
"""
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class BizError(Exception):
    def __init__(self, code: int, message: str, http_status: int = 400, data: Any = None):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.data = data


def ok(data: Any = None, message: str = "ok") -> dict:
    return {"code": 0, "data": data, "message": message}


def error(code: int, message: str, data: Any = None) -> dict:
    return {"code": code, "data": data, "message": message}


def register_exception_handlers(app) -> None:
    @app.exception_handler(BizError)
    async def _biz(_: Request, exc: BizError):
        return JSONResponse(
            status_code=exc.http_status,
            content=error(exc.code, exc.message, exc.data),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        code = {401: 40100, 403: 40300, 404: 40400}.get(exc.status_code, exc.status_code * 100)
        return JSONResponse(
            status_code=exc.status_code,
            content=error(code, str(exc.detail)),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(x) for x in first.get("loc", []) if x != "body")
        msg = f"参数错误: {loc + ' ' if loc else ''}{first.get('msg', 'invalid')}"
        return JSONResponse(status_code=422, content=error(42200, msg))

    @app.exception_handler(Exception)
    async def _unknown(_: Request, exc: Exception):
        return JSONResponse(status_code=500, content=error(50000, f"服务器内部错误: {exc}"))
