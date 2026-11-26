from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

from app.api.dependencies import get_query_service
from app.api.schemas.feedback_schema import FeedbackSchema
from app.api.schemas.query_schema import QuerySchema
from app.core.feedback import record_feedback
from app.services.query_service import QueryService

query_router = APIRouter()


@query_router.post("/api/query")
async def query_handler(
    # FastAPI 把请求体 JSON 解析成 QuerySchema
    query: QuerySchema,
    # FastAPI 调用 get_query_service，递归组装依赖
    query_service: Annotated[QueryService, Depends(get_query_service)],
):
    return StreamingResponse(
        # query.query 是用户问题字符串
        query_service.query(query.query),
        media_type="text/event-stream",
    )


@query_router.post("/api/feedback")
async def feedback_handler(feedback: FeedbackSchema):
    """结果卡点赞/点踩落盘（PRD 七.2 用户反馈 + 采纳率埋点）"""
    record_feedback(
        query_id=feedback.query_id,
        query=feedback.query,
        rating=feedback.rating,
        reason=feedback.reason,
    )
    return {"status": "ok"}
