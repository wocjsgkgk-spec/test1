from dataclasses import dataclass, field


@dataclass
class Todo:
    title: str
    id: int = 0
    completed: bool = False
    description: str = ""
    tags: list[str] = field(default_factory=list)

    def mark_done(self) -> None:
        self.completed = True

    def mark_open(self) -> None:
        self.completed = False

    def toggle(self) -> None:
        self.completed = not self.completed
