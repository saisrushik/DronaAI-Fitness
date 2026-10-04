import pytest
from httpx import AsyncClient

from tests.conftest import COACH, CUSTOMER, register, login
from tests.test_requests import OTHER_COACH, _accepted_diet_plan, _as

pytestmark = pytest.mark.asyncio

DOSA = {"name": "Masala dosa", "quantity": "2 pieces", "calories": 400,
        "protein_g": 10, "carbs_g": 60, "fat_g": 12}


async def _monday_breakfast(client: AsyncClient) -> list[dict]:
    plan = (await client.get("/api/v1/plans/mine")).json()[0]
    return plan["content"]["days"][0]["sessions"][0]["items"]


async def test_coach_only_sets_nutrition_for_new_foods(client: AsyncClient) -> None:
    plan_id, customer_id = await _accepted_diet_plan(client)
    original = await _monday_breakfast(client)
    kept = original[0]

    created = await client.post(
        "/api/v1/requests/meal",
        json={
            "plan_id": plan_id,
            "meals": [{"day": "Monday", "session": "Breakfast", "items": [kept["name"], "Masala dosa"]}],
        },
    )
    assert created.status_code == 201, created.text
    meal = created.json()["requested_meals"][0]
    assert meal["added"] == ["Masala dosa"]
    assert meal["kept"] == [kept["name"]]
    assert meal["removed"] == [i["name"] for i in original[1:]]

    await _as(client, COACH["email"])
    approved = await client.post(
        f"/api/v1/requests/{created.json()['id']}/approve-meal",
        json={"meals": [{"day": "Monday", "session": "Breakfast", "items": [DOSA]}]},
    )
    assert approved.status_code == 200, approved.text

    plan = (await client.get(f"/api/v1/coach/customers/{customer_id}")).json()["plans"][0]
    breakfast = plan["content"]["days"][0]["sessions"][0]
    assert [i["name"] for i in breakfast["items"]] == [kept["name"], "Masala dosa"]
    assert breakfast["items"][0]["calories"] == kept["calories"]
    assert breakfast["totals"]["calories"] == kept["calories"] + 400


async def test_removing_foods_needs_no_new_nutrition(client: AsyncClient) -> None:
    plan_id, _ = await _accepted_diet_plan(client)
    original = await _monday_breakfast(client)
    created = await client.post(
        "/api/v1/requests/meal",
        json={"plan_id": plan_id, "meals": [
            {"day": "Monday", "session": "Breakfast", "items": [original[0]["name"]]}
        ]},
    )
    assert created.json()["requested_meals"][0]["added"] == []

    await _as(client, COACH["email"])
    approved = await client.post(
        f"/api/v1/requests/{created.json()['id']}/approve-meal",
        json={"meals": [{"day": "Monday", "session": "Breakfast", "items": []}]},
    )
    assert approved.status_code == 200, approved.text


async def test_unchanged_meal_request_is_rejected(client: AsyncClient) -> None:
    plan_id, _ = await _accepted_diet_plan(client)
    names = [i["name"] for i in await _monday_breakfast(client)]
    response = await client.post(
        "/api/v1/requests/meal",
        json={"plan_id": plan_id, "meals": [{"day": "Monday", "session": "Breakfast", "items": names}]},
    )
    assert response.status_code == 400


async def test_coach_can_edit_and_delete_meals(client: AsyncClient) -> None:
    plan_id, _ = await _accepted_diet_plan(client)
    await _as(client, COACH["email"])

    updated = await client.put(
        f"/api/v1/coach/plans/{plan_id}/meals",
        json={"day": "Monday", "session": "Lunch", "items": [DOSA]},
    )
    assert updated.status_code == 200, updated.text
    monday = updated.json()["content"]["days"][0]
    lunch = next(s for s in monday["sessions"] if s["name"] == "Lunch")
    assert lunch["option"] == "Updated by coach"
    assert lunch["totals"]["calories"] == 400
    assert monday["totals"]["calories"] == sum(s["totals"]["calories"] for s in monday["sessions"])

    deleted = await client.delete(
        f"/api/v1/coach/plans/{plan_id}/meals", params={"day": "Monday", "session": "Snack"}
    )
    assert deleted.status_code == 200
    content = deleted.json()["content"]
    assert "Snack" not in [s["name"] for s in content["days"][0]["sessions"]]
    assert content["weekly_totals"]["calories"] == sum(d["totals"]["calories"] for d in content["days"])

    missing = await client.delete(
        f"/api/v1/coach/plans/{plan_id}/meals", params={"day": "Monday", "session": "Snack"}
    )
    assert missing.status_code == 404


async def test_other_coach_cannot_edit_meals(client: AsyncClient) -> None:
    plan_id, _ = await _accepted_diet_plan(client)
    await client.post("/api/v1/auth/logout")
    await register(client, OTHER_COACH)
    await login(client, OTHER_COACH["email"])
    response = await client.put(
        f"/api/v1/coach/plans/{plan_id}/meals",
        json={"day": "Monday", "session": "Lunch", "items": [DOSA]},
    )
    assert response.status_code == 404

    await _as(client, CUSTOMER["email"])
    customer = await client.put(
        f"/api/v1/coach/plans/{plan_id}/meals",
        json={"day": "Monday", "session": "Lunch", "items": [DOSA]},
    )
    assert customer.status_code == 403
