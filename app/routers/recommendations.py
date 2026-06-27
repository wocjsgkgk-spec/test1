from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.auth import CurrentUser
from app.models.recommendation import RecommendationItem, RecommendationResponse
from app.models.todo import Todo
from app.services.ai import (
    AIConfigurationError,
    AIRecommendationError,
    AIRecommendationService,
    get_ai_service,
)
from app.services.auth import get_current_user
from app.services.todos import list_user_todos

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def list_pending_todos(user_id: int, session: Session) -> list[Todo]:
    return list_user_todos(user_id, session, pending_only=True)


@router.post("", response_model=RecommendationResponse)
async def create_recommendations(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    ai_service: Annotated[AIRecommendationService, Depends(get_ai_service)],
    session: Annotated[Session, Depends(get_session)],
) -> RecommendationResponse:
    todos = list_pending_todos(current_user.id, session)
    if not todos:
        return RecommendationResponse(recommendations=[])

    try:
        decisions = await ai_service.recommend(todos)
    except AIConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 추천 서비스를 사용할 수 없습니다",
        ) from exc
    except AIRecommendationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI 추천을 생성하지 못했습니다",
        ) from exc

    todos_by_id = {todo.id: todo for todo in todos}
    recommendations = [
        RecommendationItem(
            priority=priority,
            todo_id=decision.todo_id,
            title=todos_by_id[decision.todo_id].title,
            due=todos_by_id[decision.todo_id].due,
            reason=decision.reason,
        )
        for priority, decision in enumerate(decisions, start=1)
    ]
    return RecommendationResponse(recommendations=recommendations)
