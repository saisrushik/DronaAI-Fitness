import pytest
from httpx import AsyncClient

from tests.conftest import COACH, CUSTOMER, CUSTOMER_PROFILE, login, register

pytestmark = pytest.mark.asyncio

OTHER_COACH = {**COACH, "email": "other.coach@test.com"}

MEALS = [{"day": "Monday", "session": "Breakfast", "items": ["Masala dosa", "Coffee"]}]
APPROVAL = {
    "meals": [
        {
            "day": "Monday",
            "session": "Breakfast",
            "items": [
                {"name": "Masala dosa", "quantity": "2 pieces", "calories": 400,
                 "protein_g": 10, "carbs_g": 60, "fat_g": 12},
                {"name": "Coffee", "quantity": "200 ml", "calories": 80,
                 "protein_g": 4, "carbs_g": 8, "fat_g": 3},
            ],
        }
    ],
    "note": "Looks good",
}


async def _as(client: AsyncClient, email: str) -> None:
    await client.post("/api/v1/auth/logout")
    await login(client, email)


async def _accepted_diet_plan(client: AsyncClient) -> tuple[str, str]:
    """Customer linked to COACH with an accepted diet plan. Leaves the customer logged in."""
    await register(client, CUSTOMER)
    await login(client, CUSTOMER["email"])
    me = (await client.put("/api/v1/auth/me/customer-profile", json=CUSTOMER_PROFILE)).json()

    await client.post("/api/v1/auth/logout")
    await register(client, COACH)
    await login(client, COACH["email"])
    linked = await client.post(
        "/api/v1/coach/customers/link", json={"share_code": me["customer"]["share_code"]}
    )
    customer_id = linked.json()["id"]
    plan = await client.post(
        f"/api/v1/coach/customers/{customer_id}/plans", json={"plan_type": "diet"}
    )
    plan_id = plan.json()["id"]

    await _as(client, CUSTOMER["email"])
    assert (await client.post(f"/api/v1/plans/{plan_id}/approve")).status_code == 200
    return plan_id, customer_id


async def _submit_meal(client: AsyncClient, plan_id: str) -> dict:
    response = await client.post(
        "/api/v1/requests/meal",
        json={"plan_id": plan_id, "meals": MEALS, "description": "South Indian please"},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_meal_request_flow_with_notifications(client: AsyncClient) -> None:
    plan_id, customer_id = await _accepted_diet_plan(client)
    request = await _submit_meal(client, plan_id)
    assert request["status"] == "pending"
    assert request["request_type"] == "meal"
    assert request["customer_name"] == "Test Customer"

    mine = (await client.get("/api/v1/notifications")).json()
    assert mine["unread"] == 1
    assert mine["items"][0]["request_id"] == request["id"]
    assert "sent to your coach" in mine["items"][0]["message"]

    # Plan content is unchanged until the coach approves.
    plan = (await client.get("/api/v1/plans/mine")).json()[0]
    breakfast = plan["content"]["days"][0]["sessions"][0]
    assert "Masala dosa" not in [i["name"] for i in breakfast["items"]]

    duplicate = await client.post(
        "/api/v1/requests/meal",
        json={"plan_id": plan_id, "meals": [{"day": "Monday", "session": "Lunch", "items": ["Rice"]}]},
    )
    assert duplicate.status_code == 409

    await _as(client, COACH["email"])
    inbox = (await client.get("/api/v1/notifications")).json()
    assert inbox["unread"] == 1
    assert inbox["items"][0]["message"] == "Test Customer sent a meal request"
    assert inbox["items"][0]["request_id"] == request["id"]

    listed = (await client.get("/api/v1/requests")).json()
    assert [r["id"] for r in listed] == [request["id"]]
    detail = (await client.get(f"/api/v1/coach/customers/{customer_id}")).json()
    assert detail["pending_requests"] == 1

    approved = await client.post(f"/api/v1/requests/{request['id']}/approve-meal", json=APPROVAL)
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    content = (await client.get(f"/api/v1/coach/customers/{customer_id}")).json()["plans"][0]["content"]
    monday = content["days"][0]
    assert [i["name"] for i in monday["sessions"][0]["items"]] == ["Masala dosa", "Coffee"]
    assert monday["sessions"][0]["totals"] == {
        "calories": 480, "protein_g": 14, "carbs_g": 68, "fat_g": 15
    }
    assert monday["totals"]["calories"] == sum(s["totals"]["calories"] for s in monday["sessions"])
    assert content["weekly_totals"]["calories"] == sum(
        d["totals"]["calories"] for d in content["days"]
    )

    again = await client.post(f"/api/v1/requests/{request['id']}/approve-meal", json=APPROVAL)
    assert again.status_code == 409

    await _as(client, CUSTOMER["email"])
    mine = (await client.get("/api/v1/notifications")).json()
    assert mine["unread"] == 2
    assert "Test Coach approved your meal request" in [n["message"] for n in mine["items"]]


async def test_approval_must_cover_requested_meals(client: AsyncClient) -> None:
    plan_id, _ = await _accepted_diet_plan(client)
    request = await _submit_meal(client, plan_id)

    await _as(client, COACH["email"])
    wrong = {**APPROVAL, "meals": [{**APPROVAL["meals"][0], "session": "Lunch"}]}
    response = await client.post(f"/api/v1/requests/{request['id']}/approve-meal", json=wrong)
    assert response.status_code == 400


async def test_meal_request_rejects_unknown_meal(client: AsyncClient) -> None:
    plan_id, _ = await _accepted_diet_plan(client)
    response = await client.post(
        "/api/v1/requests/meal",
        json={"plan_id": plan_id, "meals": [{"day": "Funday", "session": "Breakfast", "items": ["Toast"]}]},
    )
    assert response.status_code == 400


@pytest.mark.parametrize("request_type", ["workout", "injury", "query"])
async def test_other_request_types_are_answered_by_coach(
    client: AsyncClient, request_type: str
) -> None:
    await _accepted_diet_plan(client)
    created = await client.post(
        "/api/v1/requests",
        json={"request_type": request_type, "description": "My left knee hurts on squats"},
    )
    assert created.status_code == 201, created.text
    request_id = created.json()["id"]

    await _as(client, COACH["email"])
    empty = await client.post(f"/api/v1/requests/{request_id}/resolve", json={"note": " "})
    assert empty.status_code == 400
    declined = await client.post(f"/api/v1/requests/{request_id}/reject", json={"note": "No"})
    assert declined.status_code == (200 if request_type == "workout" else 400)
    if request_type == "workout":
        return
    resolved = await client.post(
        f"/api/v1/requests/{request_id}/resolve", json={"note": "Swap squats for leg press"}
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    await _as(client, CUSTOMER["email"])
    mine = (await client.get("/api/v1/requests")).json()
    assert mine[0]["coach_note"] == "Swap squats for leg press"
    messages = [n["message"] for n in (await client.get("/api/v1/notifications")).json()["items"]]
    assert any("responded to" in m for m in messages)


async def test_meal_requests_cannot_be_created_generically(client: AsyncClient) -> None:
    await _accepted_diet_plan(client)
    response = await client.post(
        "/api/v1/requests", json={"request_type": "meal", "description": "More rice please"}
    )
    assert response.status_code == 422


async def test_coach_can_reject_and_customer_can_retry(client: AsyncClient) -> None:
    plan_id, _ = await _accepted_diet_plan(client)
    request = await _submit_meal(client, plan_id)

    await _as(client, COACH["email"])
    rejected = await client.post(
        f"/api/v1/requests/{request['id']}/reject", json={"note": "Too little protein"}
    )
    assert rejected.json()["status"] == "rejected"

    await _as(client, CUSTOMER["email"])
    assert (await client.get("/api/v1/requests")).json()[0]["coach_note"] == "Too little protein"
    await _submit_meal(client, plan_id)


async def test_other_coach_cannot_review(client: AsyncClient) -> None:
    plan_id, _ = await _accepted_diet_plan(client)
    request = await _submit_meal(client, plan_id)

    await client.post("/api/v1/auth/logout")
    await register(client, OTHER_COACH)
    await login(client, OTHER_COACH["email"])
    assert (await client.get("/api/v1/requests")).json() == []
    response = await client.post(f"/api/v1/requests/{request['id']}/reject", json={})
    assert response.status_code == 404


async def test_notifications_mark_read(client: AsyncClient) -> None:
    plan_id, _ = await _accepted_diet_plan(client)
    await _submit_meal(client, plan_id)
    await client.post("/api/v1/requests", json={"request_type": "query", "description": "How much water?"})

    inbox = (await client.get("/api/v1/notifications")).json()
    assert inbox["unread"] == 2
    one = await client.post(f"/api/v1/notifications/{inbox['items'][0]['id']}/read")
    assert one.json()["read_at"] is not None
    assert (await client.get("/api/v1/notifications")).json()["unread"] == 1

    await client.post("/api/v1/notifications/read-all")
    assert (await client.get("/api/v1/notifications")).json()["unread"] == 0

    await _as(client, COACH["email"])
    other = await client.post(f"/api/v1/notifications/{inbox['items'][0]['id']}/read")
    assert other.status_code == 404
