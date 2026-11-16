"""Unit tests: call the crud functions directly, with no HTTP involved.

These are the fastest tests and pinpoint exactly which function broke.
Pattern used in every test: Arrange (set up) -> Act (call) -> Assert (check).
"""

from sqlmodel import Session

from crud_app import crud
from crud_app.models import TaskCreate, TaskUpdate


def test_create_task_assigns_id_and_defaults(session: Session) -> None:
    task = crud.create_task(session, TaskCreate(title="Learn pytest"))

    assert task.id is not None
    assert task.title == "Learn pytest"
    assert task.description is None
    assert task.completed is False


def test_get_task_returns_the_task(session: Session) -> None:
    created = crud.create_task(session, TaskCreate(title="Find me"))

    found = crud.get_task(session, created.id)

    assert found is not None
    assert found.title == "Find me"


def test_get_task_returns_none_when_missing(session: Session) -> None:
    assert crud.get_task(session, 999) is None


def test_list_tasks_returns_tasks_in_id_order(session: Session) -> None:
    for title in ["first", "second", "third"]:
        crud.create_task(session, TaskCreate(title=title))

    tasks = crud.list_tasks(session)

    assert [t.title for t in tasks] == ["first", "second", "third"]


def test_list_tasks_filters_by_completed(session: Session) -> None:
    crud.create_task(session, TaskCreate(title="done", completed=True))
    crud.create_task(session, TaskCreate(title="todo", completed=False))

    done = crud.list_tasks(session, completed=True)
    todo = crud.list_tasks(session, completed=False)

    assert [t.title for t in done] == ["done"]
    assert [t.title for t in todo] == ["todo"]


def test_list_tasks_paginates_with_offset_and_limit(session: Session) -> None:
    for i in range(5):
        crud.create_task(session, TaskCreate(title=f"task {i}"))

    page = crud.list_tasks(session, offset=1, limit=2)

    assert [t.title for t in page] == ["task 1", "task 2"]


def test_update_task_changes_only_the_fields_sent(session: Session) -> None:
    task = crud.create_task(session, TaskCreate(title="Original", description="keep me"))

    updated = crud.update_task(session, task, TaskUpdate(completed=True))

    assert updated.completed is True
    assert updated.title == "Original"  # untouched
    assert updated.description == "keep me"  # untouched


def test_delete_task_removes_it(session: Session) -> None:
    task = crud.create_task(session, TaskCreate(title="Delete me"))
    task_id = task.id

    crud.delete_task(session, task)

    assert crud.get_task(session, task_id) is None
