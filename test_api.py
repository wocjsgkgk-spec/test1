import asyncio

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app import (
    TodoCreate,
    create_app,
    create_todo,
    delete_todo,
    list_todos,
    toggle_todo,
)
from repository import InMemoryTodoRepository
from service import TodoService


def build_service() -> TodoService:
    return TodoService(InMemoryTodoRepository())


def test_create_todo_returns_201_and_defaults() -> None:
    service = build_service()
    payload = TodoCreate(title="Write docs")

    response = asyncio.run(create_todo(payload=payload, service=service))

    assert response.model_dump() == {
        "id": 1,
        "title": "Write docs",
        "completed": False,
    }


def test_list_todos_returns_created_items_in_order() -> None:
    service = build_service()
    service.create("First")
    service.create("Second")

    response = asyncio.run(list_todos(service=service))

    assert [todo.model_dump() for todo in response] == [
        {"id": 1, "title": "First", "completed": False},
        {"id": 2, "title": "Second", "completed": False},
    ]


def test_toggle_todo_flips_completed_state() -> None:
    service = build_service()
    service.create("Ship feature")

    first_toggle = asyncio.run(toggle_todo(todo_id=1, service=service))
    second_toggle = asyncio.run(toggle_todo(todo_id=1, service=service))

    assert first_toggle.completed is True
    assert second_toggle.completed is False


def test_delete_todo_removes_item() -> None:
    service = build_service()
    service.create("Delete me")

    response = asyncio.run(delete_todo(todo_id=1, service=service))

    assert response.status_code == 204
    assert service.list() == []


def test_toggle_missing_todo_returns_404() -> None:
    service = build_service()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(toggle_todo(todo_id=999, service=service))

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Todo not found"


def test_delete_missing_todo_returns_404() -> None:
    service = build_service()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(delete_todo(todo_id=999, service=service))

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Todo not found"


def test_create_todo_with_empty_title_returns_422() -> None:
    with pytest.raises(ValidationError):
        TodoCreate(title="")


def test_create_todo_with_invalid_body_returns_422() -> None:
    with pytest.raises(ValidationError):
        TodoCreate()


def test_app_registers_expected_routes() -> None:
    app = create_app()

    routes = {
        (route.path, tuple(sorted(route.methods)))
        for route in app.routes
        if hasattr(route, "methods")
    }

    assert ("/todos", ("POST",)) in routes
    assert ("/todos", ("GET",)) in routes
    assert ("/todos/{todo_id}/toggle", ("PATCH",)) in routes
    assert ("/todos/{todo_id}", ("DELETE",)) in routes
