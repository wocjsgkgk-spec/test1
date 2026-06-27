from datetime import date

from pydantic import BaseModel


class TodoCreate(BaseModel):
    title: str
    due: date | None = None


class Todo(BaseModel):
    id: int
    title: str
    done: bool = False
    due: date | None = None
