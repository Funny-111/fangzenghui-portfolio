import uuid

from fastapi import FastAPI, Request

from app.api.lifespan import lifespan
from app.api.routers.query_router import query_router
from app.core.context import request_id_ctx_var

# lifespan 管理应用启动/关闭时的资源初始化与释放
app = FastAPI(lifespan=lifespan)

# 挂载查询路由
app.include_router(query_router)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """为每个请求生成唯一 request_id，方便日志追踪"""
    request_id = uuid.uuid4()
    request_id_ctx_var.set(request_id)
    response = await call_next(request)
    return response
