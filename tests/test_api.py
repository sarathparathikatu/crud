"""API tests: send real HTTP requests to the app and check status codes + JSON.

These check what a client actually experiences: routing, validation (422),
not-found handling (404) and response shapes, on top of the CRUD logic.
"""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from crud_app import main


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ------------------------------------------------------------------ Create
def test_create_task(client: TestClient) -> None:
    response = client.post("/tasks", json={"title": "Buy milk", "description": "2 litres"})

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Buy milk"
    assert body["description"] == "2 litres"
    assert body["completed"] is False
    assert isinstance(body["id"], int)


# @pytest.mark.parametrize runs the same test once per tuple: 4 tests from 1 function.
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="missing-title"),
        pytest.param({"title": ""}, id="empty-title"),
        pytest.param({"title": "x" * 201}, id="title-too-long"),
        pytest.param({"title": "ok", "completed": "maybe"}, id="completed-not-bool"),
    ],
)
def test_create_task_rejects_invalid_payload(client: TestClient, payload: dict) -> None:
    response = client.post("/tasks", json=payload)

    assert response.status_code == 422


# ------------------------------------------------------------------ Read
def test_list_tasks_starts_empty(client: TestClient) -> None:
    response = client.get("/tasks")

    assert response.status_code == 200
    assert response.json() == []


def test_list_tasks_returns_created_tasks(client: TestClient, make_task) -> None:
    make_task(title="one")
    make_task(title="two")

    response = client.get("/tasks")

    assert [t["title"] for t in response.json()] == ["one", "two"]


def test_list_tasks_filters_by_completed(client: TestClient, make_task) -> None:
    make_task(title="done", completed=True)
    make_task(title="todo")

    response = client.get("/tasks", params={"completed": "true"})

    assert [t["title"] for t in response.json()] == ["done"]


def test_list_tasks_paginates(client: TestClient, make_task) -> None:
    for i in range(5):
        make_task(title=f"task {i}")

    response = client.get("/tasks", params={"offset": 2, "limit": 2})

    assert [t["title"] for t in response.json()] == ["task 2", "task 3"]


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 101}, {"offset": -1}],
    ids=["limit-zero", "limit-over-max", "negative-offset"],
)
def test_list_tasks_rejects_bad_pagination(client: TestClient, params: dict) -> None:
    response = client.get("/tasks", params=params)

    assert response.status_code == 422


def test_read_task(client: TestClient, make_task) -> None:
    task = make_task(title="Read me")

    response = client.get(f"/tasks/{task['id']}")

    assert response.status_code == 200
    assert response.json() == task


def test_read_missing_task_returns_404(client: TestClient) -> None:
    response = client.get("/tasks/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


# ------------------------------------------------------------------ Update
def test_update_task_partially(client: TestClient, make_task) -> None:
    task = make_task(title="Old title", description="keep me")

    response = client.patch(f"/tasks/{task['id']}", json={"title": "New title"})

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "New title"
    assert body["description"] == "keep me"
    assert body["completed"] is False


def test_update_task_can_clear_description(client: TestClient, make_task) -> None:
    task = make_task(description="temporary")

    response = client.patch(f"/tasks/{task['id']}", json={"description": None})

    assert response.status_code == 200
    assert response.json()["description"] is None


@pytest.mark.parametrize("field", ["title", "completed"])
def test_update_task_rejects_null_for_required_fields(
    client: TestClient, make_task, field: str
) -> None:
    task = make_task()

    response = client.patch(f"/tasks/{task['id']}", json={field: None})

    assert response.status_code == 422


def test_update_missing_task_returns_404(client: TestClient) -> None:
    response = client.patch("/tasks/999", json={"title": "Nope"})

    assert response.status_code == 404


# ------------------------------------------------------------------ Delete
def test_delete_task(client: TestClient, make_task) -> None:
    task = make_task()

    response = client.delete(f"/tasks/{task['id']}")

    assert response.status_code == 204
    assert client.get(f"/tasks/{task['id']}").status_code == 404


def test_delete_missing_task_returns_404(client: TestClient) -> None:
    response = client.delete("/tasks/999")

    assert response.status_code == 404


# ------------------------------------------------------------------ Startup
def test_startup_creates_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    # monkeypatch temporarily replaces an attribute and restores it after the test.
    # Here we swap the real "create tables" function for a Mock that records calls.
    fake_create = Mock()
    monkeypatch.setattr(main, "create_db_and_tables", fake_create)

    with TestClient(main.app):  # entering the context runs the startup (lifespan) code
        pass

    fake_create.assert_called_once()
