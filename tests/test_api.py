from __future__ import annotations

from datetime import date, timedelta
from typing import Any


def create_habit(client, name: str = "Read 20 pages") -> dict[str, Any]:
    response = client.post(
        "/api/v1/habits",
        json={
            "name": name,
            "description": "Daily reading",
            "category": "study",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_habit(client) -> None:
    response = client.post(
        "/api/v1/habits",
        json={
            "name": "Read 20 pages",
            "description": "Daily reading",
            "category": "study",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "Read 20 pages"
    assert payload["is_active"] is True


def test_create_habit_with_blank_name_returns_422(client) -> None:
    response = client.post("/api/v1/habits", json={"name": "   "})

    assert response.status_code == 422
    assert (
        response.json()["detail"][0]["msg"]
        == "название привычки не должно быть пустым"
    )


def test_duplicate_completion_for_same_date_returns_400(client) -> None:
    habit = create_habit(client)
    payload = {"completed_on": "2026-04-01"}

    first = client.post(
        f"/api/v1/habits/{habit['id']}/completions", json=payload
    )
    second = client.post(
        f"/api/v1/habits/{habit['id']}/completions", json=payload
    )

    assert first.status_code == 201
    assert second.status_code == 400
    assert second.json()["detail"] == "Отметка за эту дату уже существует"


def test_completion_for_missing_habit_returns_404(client) -> None:
    response = client.post(
        "/api/v1/habits/999/completions", json={"completed_on": "2026-04-01"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Привычка не найдена"


def test_future_date_returns_400(client) -> None:
    habit = create_habit(client)
    future_date = (date.today() + timedelta(days=1)).isoformat()

    response = client.post(
        f"/api/v1/habits/{habit['id']}/completions",
        json={"completed_on": future_date},
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Нельзя отмечать выполнение в будущую дату"
    )


def test_habit_stats_are_updated_after_completions(client) -> None:
    habit = create_habit(client)
    client.post(
        f"/api/v1/habits/{habit['id']}/completions",
        json={"completed_on": "2026-03-29"},
    )
    client.post(
        f"/api/v1/habits/{habit['id']}/completions",
        json={"completed_on": "2026-03-30"},
    )
    client.post(
        f"/api/v1/habits/{habit['id']}/completions",
        json={"completed_on": "2026-04-01"},
    )

    response = client.get(f"/api/v1/habits/{habit['id']}/stats")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_completions"] == 3
    assert payload["best_streak"] == 2
    assert payload["last_completed_on"] == "2026-04-01"


def test_archive_habit_disables_new_completions(client) -> None:
    habit = create_habit(client)

    archive_response = client.patch(f"/api/v1/habits/{habit['id']}/archive")
    completion_response = client.post(
        f"/api/v1/habits/{habit['id']}/completions",
        json={"completed_on": "2026-04-01"},
    )

    assert archive_response.status_code == 200
    assert archive_response.json()["is_active"] is False
    assert completion_response.status_code == 400
    assert (
        completion_response.json()["detail"]
        == "Нельзя отметить выполнение архивной привычки"
    )


def test_list_completions_returns_dates_in_desc_order(client) -> None:
    habit = create_habit(client)
    third_day = date.today() - timedelta(days=2)
    second_day = date.today() - timedelta(days=1)
    first_day = date.today()

    client.post(
        f"/api/v1/habits/{habit['id']}/completions",
        json={"completed_on": third_day.isoformat()},
    )
    client.post(
        f"/api/v1/habits/{habit['id']}/completions",
        json={"completed_on": first_day.isoformat()},
    )
    client.post(
        f"/api/v1/habits/{habit['id']}/completions",
        json={"completed_on": second_day.isoformat()},
    )

    response = client.get(f"/api/v1/habits/{habit['id']}/completions")

    assert response.status_code == 200
    assert [item["completed_on"] for item in response.json()] == [
        first_day.isoformat(),
        second_day.isoformat(),
        third_day.isoformat(),
    ]


def test_list_and_aggregate_stats(client) -> None:
    first_habit = create_habit(client, name="Workout")
    second_habit = create_habit(client, name="Meditation")

    client.post(
        f"/api/v1/habits/{first_habit['id']}/completions",
        json={"completed_on": "2026-04-01"},
    )
    client.post(
        f"/api/v1/habits/{first_habit['id']}/completions",
        json={"completed_on": "2026-04-02"},
    )
    client.patch(f"/api/v1/habits/{second_habit['id']}/archive")

    habits_response = client.get("/api/v1/habits")
    aggregate_response = client.get("/api/v1/habits/aggregated-stats")

    assert habits_response.status_code == 200
    assert len(habits_response.json()) == 2

    aggregate = aggregate_response.json()
    assert aggregate_response.status_code == 200
    assert aggregate["total_habits"] == 2
    assert aggregate["active_habits"] == 1
    assert aggregate["archived_habits"] == 1
    assert aggregate["total_completions"] == 2
    assert aggregate["max_best_streak"] == 2
