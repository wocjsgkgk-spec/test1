from repository import TodoRepository
from todo import Todo


class TodoNotFoundError(Exception):
    pass


class TodoService:
    def __init__(self, repository: TodoRepository) -> None:
        self._repository = repository

    def create(self, title: str) -> Todo:
        return self._repository.create(title=title)

    def list(self) -> list[Todo]:
        return self._repository.list()

    def toggle(self, todo_id: int) -> Todo:
        todo = self._repository.toggle(todo_id)
        if todo is None:
            raise TodoNotFoundError(todo_id)
        return todo

    def delete(self, todo_id: int) -> None:
        deleted = self._repository.delete(todo_id)
        if not deleted:
            raise TodoNotFoundError(todo_id)
