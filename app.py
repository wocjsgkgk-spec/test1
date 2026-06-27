"""기존 인메모리 API import 경로를 위한 호환 모듈."""

from app.legacy import (
    TodoCreate,
    TodoRead,
    app,
    create_app,
    create_todo,
    default_service,
    delete_todo,
    get_todo_service,
    list_todos,
    router,
    toggle_todo,
)

__all__ = [
    "TodoCreate",
    "TodoRead",
    "app",
    "create_app",
    "create_todo",
    "default_service",
    "delete_todo",
    "get_todo_service",
    "list_todos",
    "router",
    "toggle_todo",
]
