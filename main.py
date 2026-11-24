import uuid

from fastapi import FastAPI, Request

from app.api.lifespan import lifespan
from app.api.routers.query_router import query_router
from app.core.context import request_id_ctx_var

app = FastAPI(title="NEST Commerce Intelligence", version="0.1.0", lifespan=lifespan)

app.include_router(query_router)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = uuid.uuid4()
    token = request_id_ctx_var.set(request_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = str(request_id)
        return response
    finally:
        request_id_ctx_var.reset(token)
