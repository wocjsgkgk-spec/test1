from sqlalchemy import select
from sqlalchemy.orm import Session, load_only, raiseload

from app.models.todo import Todo
from app.orm_models import TodoRecord


def record_to_todo(record: TodoRecord) -> Todo:
    return Todo(
        id=record.id,
        title=record.title,
        done=record.done,
        due=record.due,
    )


def user_todos_statement(user_id: int, *, pending_only: bool = False):
    """사용자별 할 일을 필요한 컬럼만 단일 쿼리로 조회한다."""
    conditions = [TodoRecord.user_id == user_id]
    if pending_only:
        conditions.append(TodoRecord.done.is_(False))

    return (
        select(TodoRecord)
        .options(
            load_only(
                TodoRecord.id,
                TodoRecord.title,
                TodoRecord.done,
                TodoRecord.due,
                TodoRecord.user_id,
            ),
            raiseload("*"),
        )
        .where(*conditions)
        .order_by(TodoRecord.id)
    )


def owned_todo_statement(todo_id: int, user_id: int):
    """단건 수정/삭제용 소유자 제한 조회."""
    return (
        select(TodoRecord)
        .options(
            load_only(
                TodoRecord.id,
                TodoRecord.title,
                TodoRecord.done,
                TodoRecord.due,
                TodoRecord.user_id,
            ),
            raiseload("*"),
        )
        .where(
            TodoRecord.id == todo_id,
            TodoRecord.user_id == user_id,
        )
    )


def list_user_todo_records(
    user_id: int,
    session: Session,
    *,
    pending_only: bool = False,
) -> list[TodoRecord]:
    return session.scalars(
        user_todos_statement(user_id, pending_only=pending_only)
    ).all()


def list_user_todos(
    user_id: int,
    session: Session,
    *,
    pending_only: bool = False,
) -> list[Todo]:
    return [
        record_to_todo(record)
        for record in list_user_todo_records(
            user_id,
            session,
            pending_only=pending_only,
        )
    ]
