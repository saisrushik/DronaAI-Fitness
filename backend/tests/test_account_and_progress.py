from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from tests.conftest import COACH, CUSTOMER, CUSTOMER_PROFILE, login, register
from tests.test_requests import _accepted_diet_plan, _as

pytestmark = pytest.mark.asyncio

ACCOUNT = {
    "first_name": "Renamed",
    "last_name": "Person",
    "email": CUSTOMER["email"],
    "role": "customer",
    "gender": "female",
    "date_of_birth": "1990-05-20",
}


async def test_customer_edits_name_gender_and_dob(client: AsyncClient) -> None:
    await register(client, CUSTOMER)
    await login(client, CUSTOMER["email"])
    response = await client.put("/api/v1/auth/me/account", json=ACCOUNT)
    assert response.status_code == 200, response.text
    me = response.json()
    assert me["full_name"] == "Renamed Person"
    assert me["customer"]["gender"] == "female"
    assert me["customer"]["date_of_birth"] == "1990-05-20"


async def test_email_change_needs_password_and_must_be_unique(client: AsyncClient) -> None:
    await register(client, COACH)
    await register(client, CUSTOMER)
    await login(client, CUSTOMER["email"])

    changed = {**ACCOUNT, "email": "new@test.com"}
    assert (await client.put("/api/v1/auth/me/account", json=changed)).status_code == 403
    wrong = {**changed, "current_password": "Wrong123!"}
    assert (await client.put("/api/v1/auth/me/account", json=wrong)).status_code == 403
    taken = {**ACCOUNT, "email": COACH["email"], "current_password": "Password123!"}
    assert (await client.put("/api/v1/auth/me/account", json=taken)).status_code == 409

    ok = await client.put(
        "/api/v1/auth/me/account", json={**changed, "current_password": "Password123!"}
    )
    assert ok.status_code == 200
    await client.post("/api/v1/auth/logout")
    await login(client, "new@test.com")


async def test_role_switch_creates_profile_and_respects_links(client: AsyncClient) -> None:
    await _accepted_diet_plan(client)  # customer is linked to COACH

    to_coach = {**ACCOUNT, "role": "coach", "current_password": "Password123!"}
    blocked = await client.put("/api/v1/auth/me/account", json=to_coach)
    assert blocked.status_code == 409

    await _as(client, COACH["email"])
    coach_account = {
        "first_name": "Test", "last_name": "Coach", "email": COACH["email"],
        "role": "customer", "gender": "male", "date_of_birth": "1985-01-01",
        "current_password": "Password123!",
    }
    assert (await client.put("/api/v1/auth/me/account", json=coach_account)).status_code == 409

    customer_id = (await client.get("/api/v1/coach/customers")).json()[0]["id"]
    removed = await client.post(f"/api/v1/coach/customers/{customer_id}/remove")
    assert removed.status_code == 200

    switched = await client.put("/api/v1/auth/me/account", json=coach_account)
    assert switched.status_code == 200, switched.text
    me = switched.json()
    assert me["role"] == "customer"
    assert me["profile_completed"] is False
    assert me["customer"]["gender"] == "male"


async def test_removing_customer_closes_requests_and_notifies(client: AsyncClient) -> None:
    plan_id, customer_id = await _accepted_diet_plan(client)
    await client.post(
        "/api/v1/requests", json={"request_type": "query", "description": "Is rice okay at night?"}
    )

    await _as(client, COACH["email"])
    assert (await client.post(f"/api/v1/coach/customers/{customer_id}/remove")).status_code == 200
    assert (await client.get("/api/v1/coach/customers")).json() == []
    again = await client.post(f"/api/v1/coach/customers/{customer_id}/remove")
    assert again.status_code == 403

    await _as(client, CUSTOMER["email"])
    me = (await client.get("/api/v1/auth/me")).json()
    assert me["customer"]["coach_id"] is None
    requests = (await client.get("/api/v1/requests")).json()
    assert requests[0]["status"] == "rejected"
    messages = [n["message"] for n in (await client.get("/api/v1/notifications")).json()["items"]]
    assert any("removed you from their roster" in m for m in messages)


async def test_daily_progress_log_upserts(client: AsyncClient) -> None:
    await register(client, CUSTOMER)
    await login(client, CUSTOMER["email"])
    await client.put("/api/v1/auth/me/customer-profile", json=CUSTOMER_PROFILE)

    body = {
        "activities": [
            {"type": "walk", "amount": 8000},
            {"type": "other", "name": "Swimming", "amount": 20, "unit": "laps"},
        ],
        "meals": [
            {"session": "Breakfast", "status": "followed"},
            {"session": "Lunch", "status": "other", "note": "Biryani at work"},
        ],
        "mood": 4,
        "energy": 3,
        "soreness": 2,
        "sleep_hours": 7.5,
    }
    first = await client.put("/api/v1/progress/2026-10-01", json=body)
    assert first.status_code == 200, first.text
    activities = first.json()["workout"]["activities"]
    assert activities[0] == {"type": "walk", "name": "Brisk walk", "amount": 8000, "unit": "steps"}
    assert first.json()["workout"]["completed"] is True  # no planned workout that day

    updated = await client.put("/api/v1/progress/2026-10-01", json={**body, "mood": 5})
    assert updated.json()["mood"] == 5

    logs = (await client.get("/api/v1/progress", params={"days": 366})).json()
    assert len(logs) == 1
    assert logs[0]["meals"][1]["note"] == "Biryani at work"


async def test_plan_exercises_are_ticked_off_from_the_plan(client: AsyncClient) -> None:
    _, customer_id = await _accepted_diet_plan(client)
    await _as(client, COACH["email"])
    workout = await client.post(
        f"/api/v1/coach/customers/{customer_id}/plans", json={"plan_type": "workout"}
    )
    await _as(client, CUSTOMER["email"])
    plan = (await client.post(f"/api/v1/plans/{workout.json()['id']}/approve")).json()

    planned = plan["content"]["days"][0]
    names = [e["name"] for e in planned["exercises"]]
    day = date.today()
    while day.strftime("%A") != planned["day"]:
        day -= timedelta(days=1)

    url = f"/api/v1/progress/{day.isoformat()}/exercises"
    first = await client.post(url, json={"name": names[0], "done": True})
    assert first.status_code == 200, first.text
    assert first.json()["workout"]["completed"] is (len(names) == 1)

    # The daily check-in keeps exercises ticked on the plan.
    await client.put(f"/api/v1/progress/{day.isoformat()}", json={"mood": 3})
    for name in names[1:]:
        await client.post(url, json={"name": name, "done": True})
    log = (await client.get("/api/v1/progress")).json()[-1]
    assert log["mood"] == 3
    assert log["workout"]["completed"] is True

    undone = await client.post(url, json={"name": names[0], "done": False})
    assert undone.json()["workout"]["completed"] is False

    unknown = await client.post(url, json={"name": "Underwater basket weaving", "done": True})
    assert unknown.status_code == 400


@pytest.mark.parametrize(
    ("day", "payload"),
    [
        ("2999-01-01", {}),
        ("2026-10-01", {"mood": 9}),
        ("2026-10-01", {"meals": [{"session": "Lunch", "status": "followed"}] * 2}),
        ("2026-10-01", {"activities": [{"type": "run", "amount": 500}]}),
        ("2026-10-01", {"activities": [{"type": "other", "amount": 3}]}),
    ],
)
async def test_invalid_progress_logs(client: AsyncClient, day: str, payload: dict) -> None:
    await register(client, CUSTOMER)
    await login(client, CUSTOMER["email"])
    response = await client.put(f"/api/v1/progress/{day}", json=payload)
    assert response.status_code in (400, 422)
