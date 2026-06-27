from fastapi import APIRouter, Depends, FastAPI, HTTPException, Response, status
from pydantic import BaseModel, Field

from repository import InMemoryTodoRepository
from service import TodoNotFoundError, TodoService


class TodoCreate(BaseModel):
    title: str = Field(min_length=1)


class TodoRead(BaseModel):
    id: int
    title: str
    completed: bool


router = APIRouter()


def default_service() -> TodoService:
    return TodoService(InMemoryTodoRepository())


def get_todo_service() -> TodoService:
    return default_service()


@router.post("/todos", response_model=TodoRead, status_code=status.HTTP_201_CREATED)
async def create_todo(
    payload: TodoCreate,
    service: TodoService = Depends(get_todo_service),
) -> TodoRead:
    todo = service.create(title=payload.title)
    return TodoRead.model_validate(todo, from_attributes=True)


@router.get("/todos", response_model=list[TodoRead])
async def list_todos(
    service: TodoService = Depends(get_todo_service),
) -> list[TodoRead]:
    todos = service.list()
    return [TodoRead.model_validate(todo, from_attributes=True) for todo in todos]


@router.patch("/todos/{todo_id}/toggle", response_model=TodoRead)
async def toggle_todo(
    todo_id: int,
    service: TodoService = Depends(get_todo_service),
) -> TodoRead:
    try:
        todo = service.toggle(todo_id)
    except TodoNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        ) from exc
    return TodoRead.model_validate(todo, from_attributes=True)


@router.delete("/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(
    todo_id: int,
    service: TodoService = Depends(get_todo_service),
) -> Response:
    try:
        service.delete(todo_id)
    except TodoNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def create_app(service: TodoService | None = None) -> FastAPI:
    application = FastAPI(title="Todo API")
    application.include_router(router)
    if service is not None:
        application.dependency_overrides[get_todo_service] = lambda: service
    return application


app = create_app()
