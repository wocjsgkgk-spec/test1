from __future__ import annotations

from abc import ABC, abstractmethod

from todo import Todo


class TodoRepository(ABC):
    @abstractmethod
    def create(self, title: str) -> Todo:
        raise NotImplementedError

    @abstractmethod
    def list(self) -> list[Todo]:
        raise NotImplementedError

    @abstractmethod
    def get(self, todo_id: int) -> Todo | None:
        raise NotImplementedError

    @abstractmethod
    def toggle(self, todo_id: int) -> Todo | None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, todo_id: int) -> bool:
        raise NotImplementedError


class InMemoryTodoRepository(TodoRepository):
    def __init__(self) -> None:
        self._todos: list[Todo] = []
        self._next_id = 1

    def create(self, title: str) -> Todo:
        todo = Todo(id=self._next_id, title=title)
        self._todos.append(todo)
        self._next_id += 1
        return todo

    def list(self) -> list[Todo]:
        return list(self._todos)

    def get(self, todo_id: int) -> Todo | None:
        return next((todo for todo in self._todos if todo.id == todo_id), None)

    def toggle(self, todo_id: int) -> Todo | None:
        todo = self.get(todo_id)
        if todo is None:
            return None
        todo.toggle()
        return todo

    def delete(self, todo_id: int) -> bool:
        for index, todo in enumerate(self._todos):
            if todo.id == todo_id:
                del self._todos[index]
                return True
        return False
