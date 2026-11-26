from typing import Literal

from pydantic import BaseModel, Field, model_validator


class FeedbackSchema(BaseModel):
    """结果卡反馈请求体（PRD 七.2）"""
    query_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    rating: Literal["up", "down"]
    reason: str | None = None  # 点踩原因：召回错 / 生成错 / 理解错

    @model_validator(mode="after")
    def _require_reason_on_down(self):
        # PRD 七.2：点踩必须归因，否则采纳率无法回流改进
        if self.rating == "down" and not (self.reason and self.reason.strip()):
            raise ValueError("点踩必须选择原因")
        return self
