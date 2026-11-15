"""Weekly plan review (FR-5.6) and coach-applied calorie adjustment (FR-5.7)."""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from app.services.weekly_review import recommend_adjustment
from tests.conftest import COACH, CUSTOMER, CUSTOMER_PROFILE
from tests.test_requests import _accepted_diet_plan, _as

pytestmark = pytest.mark.asyncio


def _day(offset: int) -> str:
    return (date.today() - timedelta(days=offset)).isoformat()


async def _weigh_in(client: AsyncClient, days_ago: int, kg: float) -> None:
    response = await client.post(
        "/api/v1/measurements",
        json={"weight_kg": kg, "recorded_at": f"{_day(days_ago)}T08:00:00Z"},
    )
    assert response.status_code == 201, response.text


async def _check_in(client: AsyncClient, days_ago: int, meal_status: str = "followed") -> None:
    response = await client.put(
        f"/api/v1/progress/{_day(days_ago)}",
        json={"meals": [{"session": "Breakfast", "status": meal_status}], "mood": 4,
              "sleep_hours": 7},
    )
    assert response.status_code == 200, response.text


async def _logged_week(
    client: AsyncClient, *, weights=(85.0, 85.0), days=3, meal_status="followed"
) -> str:
    """Lose-fat customer linked to COACH with a week of logs. Leaves the customer logged in."""
    _, customer_id = await _accepted_diet_plan(client)
    await _weigh_in(client, 8, weights[0])
    await _weigh_in(client, 1, weights[1])
    for offset in range(1, days + 1):
        await _check_in(client, offset, meal_status)
    return customer_id


async def _reviews(client: AsyncClient) -> list[dict]:
    response = await client.get("/api/v1/progress/reviews")
    assert response.status_code == 200, response.text
    return response.json()


async def test_review_is_created_once_a_week_of_logs_exists(client: AsyncClient) -> None:
    await _logged_week(client)

    reviews = await _reviews(client)
    assert len(reviews) == 1
    review = reviews[0]
    assert review["period_end"] == _day(1)
    assert review["period_start"] == _day(7)
    assert review["stats"]["days_logged"] == 3
    assert review["stats"]["meal_adherence"] == 100
    assert review["stats"]["weekly_change_kg"] == 0
    # Lose fat expects about -0.36 kg a week; no change means eat less, capped at 200 kcal.
    assert review["recommended_adjustment"] == -200
    assert review["status"] == "open"

    # More logs in the same week don't create another review.
    await _check_in(client, 4)
    assert len(await _reviews(client)) == 1


async def test_no_review_without_enough_logged_days(client: AsyncClient) -> None:
    await _accepted_diet_plan(client)
    await _check_in(client, 9)  # makes the first week due
    await _check_in(client, 1)
    await _check_in(client, 2)
    assert await _reviews(client) == []


async def test_no_review_before_a_full_week_has_passed(client: AsyncClient) -> None:
    await _accepted_diet_plan(client)
    for offset in (1, 2, 3):
        await _check_in(client, offset)
    assert await _reviews(client) == []


async def test_on_track_weight_needs_no_adjustment(client: AsyncClient) -> None:
    await _logged_week(client, weights=(85.0, 84.6))
    review = (await _reviews(client))[0]
    assert review["recommended_adjustment"] == 0
    assert review["status"] == "none"
    assert "on track" in review["summary"]


async def test_low_meal_adherence_blocks_calorie_changes(client: AsyncClient) -> None:
    await _logged_week(client, meal_status="other")
    review = (await _reviews(client))[0]
    assert review["recommended_adjustment"] == 0
    assert "0% of logged meals" in review["summary"]


async def test_coach_applies_adjustment_to_the_calorie_target(client: AsyncClient) -> None:
    customer_id = await _logged_week(client)
    before = (await client.get("/api/v1/auth/me")).json()["metrics"]["target_calories"]

    await _as(client, COACH["email"])
    messages = [n["message"] for n in (await client.get("/api/v1/notifications")).json()["items"]]
    assert any("weekly review" in m and "-200 kcal" in m for m in messages)

    detail = (await client.get(f"/api/v1/coach/customers/{customer_id}")).json()
    review_id = detail["reviews"][0]["id"]
    applied = await client.post(f"/api/v1/coach/reviews/{review_id}/apply")
    assert applied.status_code == 200, applied.text
    assert applied.json()["status"] == "applied"
    again = await client.post(f"/api/v1/coach/reviews/{review_id}/apply")
    assert again.status_code == 409

    detail = (await client.get(f"/api/v1/coach/customers/{customer_id}")).json()
    assert detail["calorie_adjustment"] == -200
    assert detail["metrics"]["calorie_breakdown"]["coach_adjustment"] == -200
    assert detail["metrics"]["target_calories"] == before - 200

    plan = await client.post(
        f"/api/v1/coach/customers/{customer_id}/plans", json={"plan_type": "diet"}
    )
    assert plan.json()["content"]["targets"]["target_calories"] == before - 200

    # Changing goal starts the adjustment over.
    await _as(client, CUSTOMER["email"])
    me = await client.put(
        "/api/v1/auth/me/customer-profile", json={**CUSTOMER_PROFILE, "primary_goal": "maintain"}
    )
    assert me.json()["metrics"]["calorie_breakdown"]["coach_adjustment"] == 0


async def test_coach_can_dismiss_and_others_cannot_act(client: AsyncClient) -> None:
    customer_id = await _logged_week(client)
    review_id = (await _reviews(client))[0]["id"]

    # Customers can't apply their own adjustment.
    assert (await client.post(f"/api/v1/coach/reviews/{review_id}/apply")).status_code == 403

    await client.post("/api/v1/auth/logout")
    await client.post("/api/v1/auth/register", json={**COACH, "email": "other@test.com"})
    assert (await client.post(f"/api/v1/coach/reviews/{review_id}/dismiss")).status_code == 403

    await _as(client, COACH["email"])
    dismissed = await client.post(f"/api/v1/coach/reviews/{review_id}/dismiss")
    assert dismissed.json()["status"] == "dismissed"
    detail = (await client.get(f"/api/v1/coach/customers/{customer_id}")).json()
    assert detail["calorie_adjustment"] == 0


async def test_goal_change_retires_a_pending_suggestion(client: AsyncClient) -> None:
    await _logged_week(client)
    changed = await client.put(
        "/api/v1/auth/me/customer-profile", json={**CUSTOMER_PROFILE, "primary_goal": "lean_bulk"}
    )
    assert changed.status_code == 200
    review = (await _reviews(client))[0]
    assert review["status"] == "superseded"

    await _as(client, COACH["email"])
    assert (await client.post(f"/api/v1/coach/reviews/{review['id']}/apply")).status_code == 409


@pytest.mark.parametrize(
    ("rate", "current", "expected"),
    [
        (-1.4, 0, 200),  # losing faster than 1 kg/week: eat more
        (0.8, 0, -200),  # gaining faster than 0.5 kg/week: eat less
        (0.0, -400, -100),  # a step can't take the running total past -500
        (0.0, -500, 0),
    ],
)
def test_recommendation_respects_safety_limits(rate, current, expected):
    adjustment, reason = recommend_adjustment("lose_fat", rate, 100, current)
    assert adjustment == expected
    assert reason


def test_no_recommendation_without_weigh_ins():
    adjustment, reason = recommend_adjustment("lose_fat", None, 100, 0)
    assert adjustment == 0
    assert "weigh-ins" in reason
