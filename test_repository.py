from repository import InMemoryTodoRepository


def test_repository_assigns_incrementing_ids() -> None:
    repository = InMemoryTodoRepository()

    first = repository.create("First")
    second = repository.create("Second")

    assert first.id == 1
    assert second.id == 2


def test_repository_keeps_incrementing_ids_after_delete() -> None:
    repository = InMemoryTodoRepository()
    repository.create("First")
    repository.create("Second")

    assert repository.delete(1) is True

    third = repository.create("Third")

    assert third.id == 3


def test_repository_list_matches_current_state() -> None:
    repository = InMemoryTodoRepository()
    repository.create("First")
    repository.create("Second")
    repository.toggle(2)
    repository.delete(1)

    todos = repository.list()

    assert len(todos) == 1
    assert todos[0].id == 2
    assert todos[0].title == "Second"
    assert todos[0].completed is True
