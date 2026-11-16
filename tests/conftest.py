"""Shared pytest fixtures.

pytest loads this file automatically. Any test can use a fixture just by naming
it as a parameter, e.g. `def test_something(client): ...`.
"""

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from crud_app.database import get_session
from crud_app.main import app


@pytest.fixture
def session() -> Iterator[Session]:
    """A brand-new, empty database for every single test.

    - "sqlite://" is an in-memory database: fast, and nothing is written to disk.
    - StaticPool makes every connection share that one in-memory database.
    - Because each test gets its own engine, tests can never affect each other.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session  # the test runs here
    engine.dispose()  # teardown: runs after the test, even if it failed


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    """An HTTP client for the app, wired to the test database.

    dependency_overrides tells FastAPI: "wherever a route asks for get_session,
    give it this test session instead". The app code doesn't change at all.
    """
    app.dependency_overrides[get_session] = lambda: session
    # Not used as `with TestClient(app)`, so the startup hook (which would create
    # a real tasks.db file) does not run. The `session` fixture made the tables.
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def make_task(client: TestClient) -> Callable[..., dict[str, Any]]:
    """Factory fixture: returns a function that creates a task through the API.

    Usage in a test:  task = make_task(title="Buy milk", completed=True)
    """

    def _make_task(**fields: Any) -> dict[str, Any]:
        payload = {"title": "Write tests", **fields}
        response = client.post("/tasks", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _make_task
