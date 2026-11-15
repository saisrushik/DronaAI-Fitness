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


async def _ask_question(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/requests", json={"request_type": "query", "description": "Is rice okay at night?"}
    )
    assert response.status_code == 201, response.text


async def test_customer_can_leave_and_change_coach(client: AsyncClient) -> None:
    await _accepted_diet_plan(client)
    await _ask_question(client)

    left = await client.post("/api/v1/plans/my-coach/leave")
    assert left.status_code == 200, left.text
    assert (await client.post("/api/v1/plans/my-coach/leave")).status_code == 400

    me = (await client.get("/api/v1/auth/me")).json()
    assert me["customer"]["coach_id"] is None
    assert (await client.get("/api/v1/plans/my-coach")).json() is None
    assert (await client.get("/api/v1/requests")).json()[0]["status"] == "rejected"
    plans = (await client.get("/api/v1/plans/mine")).json()
    assert plans and plans[0]["content"] is not None

    await _as(client, COACH["email"])
    assert (await client.get("/api/v1/coach/customers")).json() == []
    messages = [n["message"] for n in (await client.get("/api/v1/notifications")).json()["items"]]
    assert any("left your roster" in m for m in messages)

    # The share code now works for a different coach.
    await client.post("/api/v1/auth/logout")
    await register(client, {**COACH, "email": "new.coach@test.com"})
    linked = await client.post(
        "/api/v1/coach/customers/link", json={"share_code": me["customer"]["share_code"]}
    )
    assert linked.status_code == 200, linked.text


async def test_coach_cannot_use_leave(client: AsyncClient) -> None:
    await register(client, COACH)
    assert (await client.post("/api/v1/plans/my-coach/leave")).status_code == 403


async def test_customer_data_export(client: AsyncClient) -> None:
    await _accepted_diet_plan(client)
    await _ask_question(client)

    response = await client.get("/api/v1/auth/me/export")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    data = response.json()
    assert data["account"]["email"] == CUSTOMER["email"]
    assert "password_hash" not in data["account"]
    assert data["customer_profile"]["height_cm"] == CUSTOMER_PROFILE["height_cm"]
    assert data["coach"]["full_name"] == "Test Coach"
    assert data["plans"][0]["content"] is not None
    assert data["body_measurements"]
    assert data["requests"][0]["request_type"] == "query"
    assert data["health_metrics"]["bmr"] > 0
    assert all("refresh_jti" not in s for s in data["sign_in_sessions"])


async def test_coach_export_excludes_customer_data(client: AsyncClient) -> None:
    await _accepted_diet_plan(client)
    await _as(client, COACH["email"])

    data = (await client.get("/api/v1/auth/me/export")).json()
    assert data["coach_profile"] is not None
    assert "plans" not in data and "customer_profile" not in data


async def _rows_for_customer(client: AsyncClient, customer_id: str) -> int:
    from uuid import UUID

    from sqlalchemy import func, select

    from app.db.models import (
        BodyMeasurement,
        Customer,
        CustomerRequest,
        ProgressLog,
        WorkoutDietPlan,
    )

    cid = UUID(customer_id)
    async with client.session_factory() as db:  # type: ignore[attr-defined]
        total = await db.scalar(select(func.count()).select_from(Customer).where(Customer.id == cid))
        for model in (BodyMeasurement, CustomerRequest, ProgressLog, WorkoutDietPlan):
            total += await db.scalar(
                select(func.count()).select_from(model).where(model.customer_id == cid)
            )
    return total


async def test_customer_deletes_account_and_all_data(client: AsyncClient) -> None:
    _, customer_id = await _accepted_diet_plan(client)
    await _ask_question(client)
    logged = await client.put(f"/api/v1/progress/{date.today().isoformat()}", json={"mood": 4})
    assert logged.status_code == 200, logged.text
    assert await _rows_for_customer(client, customer_id) > 0

    wrong = await client.post("/api/v1/auth/me/delete", json={"password": "Wrong123!"})
    assert wrong.status_code == 403

    deleted = await client.post("/api/v1/auth/me/delete", json={"password": "Password123!"})
    assert deleted.status_code == 200, deleted.text
    assert await _rows_for_customer(client, customer_id) == 0
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    gone = await client.post(
        "/api/v1/auth/login", json={"email": CUSTOMER["email"], "password": "Password123!"}
    )
    assert gone.status_code == 401

    await login(client, COACH["email"])
    assert (await client.get("/api/v1/coach/customers")).json() == []


async def test_deleted_coach_releases_customers_who_keep_their_plans(client: AsyncClient) -> None:
    await _accepted_diet_plan(client)
    await _ask_question(client)

    await _as(client, COACH["email"])
    deleted = await client.post("/api/v1/auth/me/delete", json={"password": "Password123!"})
    assert deleted.status_code == 200, deleted.text

    await login(client, CUSTOMER["email"])
    me = (await client.get("/api/v1/auth/me")).json()
    assert me["customer"]["coach_id"] is None
    plans = (await client.get("/api/v1/plans/mine")).json()
    assert plans[0]["content"] is not None and plans[0]["coach_id"] is None
    assert (await client.get("/api/v1/requests")).json()[0]["status"] == "rejected"
    messages = [n["message"] for n in (await client.get("/api/v1/notifications")).json()["items"]]
    assert any("closed their account" in m for m in messages)


async def test_email_change_signs_out_other_devices(client: AsyncClient) -> None:
    await register(client, CUSTOMER)
    other_device = client.cookies.get("fitness_session")
    client.cookies.clear()
    await login(client, CUSTOMER["email"])

    changed = await client.put(
        "/api/v1/auth/me/account",
        json={**ACCOUNT, "email": "moved@test.com", "current_password": "Password123!"},
    )
    assert changed.status_code == 200
    current = client.cookies.get("fitness_session")
    client.cookies.clear()

    def bearer(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    assert (await client.get("/api/v1/auth/me", headers=bearer(current))).status_code == 200
    assert (await client.get("/api/v1/auth/me", headers=bearer(other_device))).status_code == 401


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


# --- Profile data and onboarding (BRD 4.1, FR-1.5, FR-1.8) ---

SLIM_CUSTOMER = {
    key: CUSTOMER[key]
    for key in ("first_name", "last_name", "email", "password", "role", "accepted_disclaimer",
                "date_of_birth", "gender")
}

FULL_PROFILE = {
    **CUSTOMER_PROFILE,
    "primary_goal": "recomp",
    "budget_level": "low",
    "medical_conditions": ["asthma", "asthma", "thyroid"],
    "stress_level": "high",
    "injuries": [
        {"body_part": "knee", "severity": "moderate", "recovery_status": "recovering",
         "date_of_injury": "2024-02-01", "notes": " Twisted on stairs "},
    ],
    "training_experience": "beginner",
    "training_location": "home",
    "training_days_per_week": 3,
}


async def _messages(client: AsyncClient) -> list[str]:
    return [n["message"] for n in (await client.get("/api/v1/notifications")).json()["items"]]


async def test_slim_signup_then_onboarding_saves_the_full_profile(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register", json={**SLIM_CUSTOMER, "country": "in"}
    )
    assert response.status_code == 201, response.text
    me = response.json()
    assert me["customer"]["country"] == "IN"
    assert me["profile_completed"] is False
    assert (await client.get("/api/v1/measurements")).json() == []

    saved = await client.put("/api/v1/auth/me/customer-profile", json=FULL_PROFILE)
    assert saved.status_code == 200, saved.text
    customer = saved.json()["customer"]
    assert customer["primary_goal"] == "recomp"
    assert customer["medical_conditions"] == ["asthma", "thyroid"]
    assert customer["injuries"][0]["body_part"] == "knee"
    assert customer["injuries"][0]["notes"] == "Twisted on stairs"
    assert customer["training_location"] == "home"
    assert saved.json()["metrics"]["bmi"]["primary"] == "asian"
    # The body step of onboarding starts the measurement history.
    assert len((await client.get("/api/v1/measurements")).json()) == 1


async def test_signup_still_needs_age_and_gender(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register", json={**SLIM_CUSTOMER, "gender": None}
    )
    assert response.status_code == 422
    assert "gender" in response.text


@pytest.mark.parametrize(
    "change",
    [
        {"primary_goal": "build_muscle"},
        {"training_days_per_week": 7},
        {"training_location": "park"},
        {"medical_conditions": ["broken heart"]},
        {"injuries": [{"body_part": "toe", "severity": "mild", "recovery_status": "recovered"}]},
        {"injuries": [{"body_part": "knee", "severity": "mild", "recovery_status": "recovered",
                       "date_of_injury": "2999-01-01"}]},
    ],
)
async def test_invalid_profile_values_are_rejected(client: AsyncClient, change: dict) -> None:
    await register(client, SLIM_CUSTOMER)
    response = await client.put(
        "/api/v1/auth/me/customer-profile", json={**FULL_PROFILE, **change}
    )
    assert response.status_code == 422


async def test_country_change_switches_primary_bmi_standard(client: AsyncClient) -> None:
    await register(client, SLIM_CUSTOMER)
    await client.put("/api/v1/auth/me/customer-profile", json=FULL_PROFILE)

    response = await client.put("/api/v1/auth/me/account", json={**ACCOUNT, "country": "GB"})
    assert response.status_code == 200, response.text
    assert response.json()["customer"]["country"] == "GB"
    assert response.json()["metrics"]["bmi"]["primary"] == "who"


async def test_coach_is_told_when_a_linked_customer_completes_their_profile(
    client: AsyncClient,
) -> None:
    me = (await client.post("/api/v1/auth/register", json=SLIM_CUSTOMER)).json()
    await client.post("/api/v1/auth/logout")
    await register(client, COACH)
    linked = await client.post(
        "/api/v1/coach/customers/link", json={"share_code": me["customer"]["share_code"]}
    )
    customer_id = linked.json()["id"]

    await _as(client, CUSTOMER["email"])
    await client.put("/api/v1/auth/me/customer-profile", json=FULL_PROFILE)

    await _as(client, COACH["email"])
    assert any("completed their profile" in m for m in await _messages(client))
    detail = (await client.get(f"/api/v1/coach/customers/{customer_id}")).json()
    # Nothing to regenerate yet: no plan existed before the profile was finished.
    assert detail["profile_updated_at"] is None
    assert detail["injuries"][0]["body_part"] == "knee"


async def test_profile_change_flags_plans_for_regeneration(client: AsyncClient) -> None:
    _, customer_id = await _accepted_diet_plan(client)

    # Saving the same values again isn't a change.
    unchanged = await client.put("/api/v1/auth/me/customer-profile", json=CUSTOMER_PROFILE)
    assert unchanged.status_code == 200
    await _as(client, COACH["email"])
    assert not any("updated their profile" in m for m in await _messages(client))
    detail = (await client.get(f"/api/v1/coach/customers/{customer_id}")).json()
    assert detail["profile_updated_at"] is None

    await _as(client, CUSTOMER["email"])
    changed = await client.put(
        "/api/v1/auth/me/customer-profile", json={**CUSTOMER_PROFILE, "primary_goal": "strength"}
    )
    assert changed.status_code == 200

    await _as(client, COACH["email"])
    assert any("updated their profile" in m for m in await _messages(client))
    detail = (await client.get(f"/api/v1/coach/customers/{customer_id}")).json()
    assert detail["profile_updated_at"] is not None
    assert detail["profile_updated_at"] >= detail["plans"][0]["created_at"]

    regenerated = await client.post(
        f"/api/v1/coach/customers/{customer_id}/plans", json={"plan_type": "workout"}
    )
    assert regenerated.json()["content"]["goal"] == "strength"


async def test_unit_preference_is_saved_per_user(client: AsyncClient) -> None:
    await register(client, SLIM_CUSTOMER)
    assert (await client.get("/api/v1/auth/me")).json()["unit_system"] == "metric"

    saved = await client.put("/api/v1/auth/me/preferences", json={"unit_system": "imperial"})
    assert saved.status_code == 200
    assert saved.json()["unit_system"] == "imperial"
    bad = await client.put("/api/v1/auth/me/preferences", json={"unit_system": "stones"})
    assert bad.status_code == 422
