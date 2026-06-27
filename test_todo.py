from todo import Todo


def test_todo_defaults():
    todo = Todo(title="Write tests")

    assert todo.title == "Write tests"
    assert todo.completed is False
    assert todo.description == ""
    assert todo.tags == []


def test_todo_status_methods():
    todo = Todo(title="Ship feature")

    todo.mark_done()
    assert todo.completed is True

    todo.mark_open()
    assert todo.completed is False
