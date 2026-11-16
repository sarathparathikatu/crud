"""HTTP layer: FastAPI routes that turn HTTP requests into CRUD calls.

Run it locally with:   uv run fastapi dev src/crud_app/main.py
Interactive docs at:   http://127.0.0.1:8000/docs
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlmodel import Session

from crud_app import crud
from crud_app.database import create_db_and_tables, get_session
from crud_app.models import Task, TaskCreate, TaskPublic, TaskUpdate


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    create_db_and_tables()  # runs once, when the server starts
    yield


app = FastAPI(title="Task Manager API", version="0.1.0", lifespan=lifespan)

# "Dependency injection": any route that declares a SessionDep parameter gets a
# database session from get_session(). Tests swap that function out.
SessionDep = Annotated[Session, Depends(get_session)]


def get_task_or_404(task_id: int, session: SessionDep) -> Task:
    task = crud.get_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


# Routes that need an existing task declare TaskDep, so the 404 check is written once.
TaskDep = Annotated[Task, Depends(get_task_or_404)]


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check, used by the Docker smoke test in CI."""
    return {"status": "broken"}


@app.post("/tasks", response_model=TaskPublic, status_code=status.HTTP_201_CREATED)
def create_task(task_in: TaskCreate, session: SessionDep) -> Task:
    return crud.create_task(session, task_in)


@app.get("/tasks", response_model=list[TaskPublic])
def list_tasks(
    session: SessionDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    completed: bool | None = None,
) -> list[Task]:
    return crud.list_tasks(session, offset=offset, limit=limit, completed=completed)


@app.get("/tasks/{task_id}", response_model=TaskPublic)
def read_task(task: TaskDep) -> Task:
    return task


@app.patch("/tasks/{task_id}", response_model=TaskPublic)
def update_task(task: TaskDep, task_in: TaskUpdate, session: SessionDep) -> Task:
    return crud.update_task(session, task, task_in)


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task: TaskDep, session: SessionDep) -> None:
    crud.delete_task(session, task)
