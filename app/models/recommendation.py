from datetime import date

from pydantic import BaseModel, Field, field_validator


class PriorityDecision(BaseModel):
    todo_id: int
    reason: str = Field(min_length=1, max_length=200)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, reason: str) -> str:
        normalized = reason.strip()
        if not normalized or "\n" in normalized or "\r" in normalized:
            raise ValueError("reason은 한 줄이어야 합니다")
        return normalized


class PriorityDecisionList(BaseModel):
    recommendations: list[PriorityDecision]


class RecommendationItem(BaseModel):
    priority: int
    todo_id: int
    title: str
    due: date | None = None
    reason: str


class RecommendationResponse(BaseModel):
    recommendations: list[RecommendationItem]
