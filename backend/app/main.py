import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .response import register_exception_handlers
from .routers import admin, auth, comments, fitness, players, promotions, training

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("training-archive")


class AccessLogMiddleware(BaseHTTPMiddleware):
    """请求日志 + 兜底保证错误响应也是 {code,data,message} 结构。"""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api"):
            log.info("%s %s -> %s", request.method, request.url.path, response.status_code)
        return response


app = FastAPI(
    title="省队青训营训练档案平台 API",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AccessLogMiddleware)

register_exception_handlers(app)

API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(players.router, prefix=API_PREFIX)
app.include_router(training.router, prefix=API_PREFIX)
app.include_router(fitness.router, prefix=API_PREFIX)
app.include_router(comments.router, prefix=API_PREFIX)
app.include_router(promotions.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)


@app.get("/health", tags=["系统"])
async def health():
    return {"code": 0, "data": {"status": "up"}, "message": "ok"}
