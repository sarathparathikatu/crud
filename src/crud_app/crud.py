"""Data-access layer: the four CRUD operations, with no HTTP concepts in sight.

Keeping these as plain functions that take a Session makes them easy to unit
test directly (see tests/test_crud.py) and easy to reuse outside the web app.
"""

from sqlmodel import Session, select

from crud_app.models import Task, TaskCreate, TaskUpdate


def create_task(session: Session, task_in: TaskCreate) -> Task:
    task = Task.model_validate(task_in)
    session.add(task)
    session.commit()
    session.refresh(task)  # reload so the database-generated id is filled in
    return task


def get_task(session: Session, task_id: int) -> Task | None:
    return session.get(Task, task_id)


def list_tasks(
    session: Session,
    *,
    offset: int = 0,
    limit: int = 100,
    completed: bool | None = None,
) -> list[Task]:
    statement = select(Task)
    if completed is not None:
        statement = statement.where(Task.completed == completed)
    statement = statement.order_by(Task.id).offset(offset).limit(limit)
    return list(session.exec(statement).all())


def update_task(session: Session, task: Task, task_in: TaskUpdate) -> Task:
    # exclude_unset=True keeps only the fields the client actually sent, which
    # is what makes this a *partial* update.
    changes = task_in.model_dump(exclude_unset=True)
    task.sqlmodel_update(changes)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def delete_task(session: Session, task: Task) -> None:
    session.delete(task)
    session.commit()
