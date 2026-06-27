from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.auth import CurrentUser
from app.models.todo import Todo, TodoCreate
from app.orm_models import TodoRecord
from app.services import ai
from app.services.ai import PrioritySuggestion
from app.services.auth import get_current_user
from app.services.todos import (
    list_user_todos,
    owned_todo_statement,
    record_to_todo,
)

router = APIRouter(prefix="/todos", tags=["todos"])


# 기존 todo_api import 경로를 위한 호환 별칭.
row_to_todo = record_to_todo


def get_todo(todo_id: int, user_id: int, session: Session) -> Todo:
    record = session.scalar(owned_todo_statement(todo_id, user_id))
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="할 일을 찾을 수 없습니다",
        )
    return record_to_todo(record)


@router.post("", response_model=Todo, status_code=status.HTTP_201_CREATED)
async def create_todo(
    payload: TodoCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Todo:
    title = payload.title.strip()
    if not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="제목은 필수입니다",
        )

    record = TodoRecord(
        title=title,
        due=payload.due,
        user_id=current_user.id,
    )
    session.add(record)
    session.commit()
    return get_todo(record.id, current_user.id, session)


@router.get("", response_model=list[Todo])
async def list_todos(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> list[Todo]:
    return list_user_todos(current_user.id, session)


@router.get("/suggest", response_model=list[PrioritySuggestion])
async def suggest_todo_priorities(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> list[PrioritySuggestion]:
    return ai.suggest_priority(
        list_user_todos(current_user.id, session, pending_only=True)
    )


@router.patch("/{todo_id}/toggle", response_model=Todo)
async def toggle_todo(
    todo_id: int,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Todo:
    record = session.scalar(owned_todo_statement(todo_id, current_user.id))
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="할 일을 찾을 수 없습니다",
        )
    record.done = not record.done
    session.commit()
    return record_to_todo(record)


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(
    todo_id: int,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    record = session.scalar(owned_todo_statement(todo_id, current_user.id))
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="할 일을 찾을 수 없습니다",
        )
    session.delete(record)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
