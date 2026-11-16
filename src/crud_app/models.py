"""Data models.

A SQLModel class is a Pydantic model (validation) and, with `table=True`, also a
SQLAlchemy table (storage). We split them by purpose:

    TaskBase    fields shared by the others
    Task        the database table
    TaskCreate  what a client sends to create a task   (POST body)
    TaskUpdate  what a client sends to change a task   (PATCH body, all optional)
    TaskPublic  what the API sends back                (always has an id)
"""

from pydantic import field_validator
from sqlmodel import Field, SQLModel


class TaskBase(SQLModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    completed: bool = False


class Task(TaskBase, table=True):
    id: int | None = Field(default=None, primary_key=True)


class TaskCreate(TaskBase):
    pass


class TaskPublic(TaskBase):
    id: int


class TaskUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    completed: bool | None = None

    @field_validator("title", "completed")
    @classmethod
    def reject_explicit_null(cls, value: str | bool | None) -> str | bool:
        # Leaving a field out of a PATCH body means "don't change it". Sending
        # null for a column that can't be empty would crash the database, so we
        # turn it into a clear 422 validation error instead.
        if value is None:
            raise ValueError("may be omitted, but cannot be null")
        return value
