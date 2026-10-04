import pytest
from httpx import AsyncClient

from tests.conftest import COACH, CUSTOMER, CUSTOMER_PROFILE, login, register

pytestmark = pytest.mark.asyncio

OTHER_COACH = {**COACH, "email": "other.coach@test.com"}


async def _customer_with_profile(client: AsyncClient) -> dict:
    await register(client, CUSTOMER)
    await login(client, CUSTOMER["email"])
    response = await client.put("/api/v1/auth/me/customer-profile", json=CUSTOMER_PROFILE)
    assert response.status_code == 200, response.text
    return response.json()


async def test_customer_cannot_access_coach_endpoints(client: AsyncClient) -> None:
    await _customer_with_profile(client)
    assert (await client.get("/api/v1/coach/customers")).status_code == 403


async def test_coach_cannot_access_customer_endpoints(client: AsyncClient) -> None:
    await register(client, COACH)
    await login(client, COACH["email"])
    assert (await client.get("/api/v1/plans/mine")).status_code == 403


async def test_coach_needs_share_code_to_add_customer(client: AsyncClient) -> None:
    me = await _customer_with_profile(client)
    share_code = me["customer"]["share_code"]

    await client.post("/api/v1/auth/logout")
    await register(client, COACH)
    await login(client, COACH["email"])

    bad = await client.post("/api/v1/coach/customers/link", json={"share_code": "WRONGCOD"})
    assert bad.status_code == 404

    good = await client.post("/api/v1/coach/customers/link", json={"share_code": share_code})
    assert good.status_code == 200
    assert good.json()["full_name"] == "Test Customer"


async def test_coach_cannot_touch_another_coachs_customer(client: AsyncClient) -> None:
    me = await _customer_with_profile(client)
    share_code = me["customer"]["share_code"]

    await client.post("/api/v1/auth/logout")
    await register(client, COACH)
    await login(client, COACH["email"])
    linked = await client.post("/api/v1/coach/customers/link", json={"share_code": share_code})
    customer_id = linked.json()["id"]

    await client.post("/api/v1/auth/logout")
    await register(client, OTHER_COACH)
    await login(client, OTHER_COACH["email"])

    assert (await client.get(f"/api/v1/coach/customers/{customer_id}")).status_code == 403
    generate = await client.post(
        f"/api/v1/coach/customers/{customer_id}/plans", json={"plan_type": "workout"}
    )
    assert generate.status_code == 403


async def test_plan_content_withheld_until_customer_approves(client: AsyncClient) -> None:
    me = await _customer_with_profile(client)
    share_code = me["customer"]["share_code"]

    await client.post("/api/v1/auth/logout")
    await register(client, COACH)
    await login(client, COACH["email"])
    linked = await client.post("/api/v1/coach/customers/link", json={"share_code": share_code})
    customer_id = linked.json()["id"]
    created = await client.post(
        f"/api/v1/coach/customers/{customer_id}/plans", json={"plan_type": "diet"}
    )
    assert created.status_code == 201
    plan_id = created.json()["id"]

    await client.post("/api/v1/auth/logout")
    await login(client, CUSTOMER["email"])

    plans = (await client.get("/api/v1/plans/mine")).json()
    assert plans[0]["content"] is None
    assert plans[0]["approved_at"] is None

    approved = await client.post(f"/api/v1/plans/{plan_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["content"]["days"]
    assert approved.json()["approved_at"]


async def test_customer_cannot_approve_someone_elses_plan(client: AsyncClient) -> None:
    await _customer_with_profile(client)
    response = await client.post("/api/v1/plans/00000000-0000-0000-0000-000000000000/approve")
    assert response.status_code == 404


async def test_share_code_is_single_use(client: AsyncClient) -> None:
    me = await _customer_with_profile(client)
    share_code = me["customer"]["share_code"]

    await client.post("/api/v1/auth/logout")
    await register(client, COACH)
    await login(client, COACH["email"])
    linked = await client.post("/api/v1/coach/customers/link", json={"share_code": share_code})
    customer_id = linked.json()["id"]
    removed = await client.post(f"/api/v1/coach/customers/{customer_id}/remove")
    assert removed.status_code == 200

    # The removed customer can't be re-added with the code the coach already saw.
    again = await client.post("/api/v1/coach/customers/link", json={"share_code": share_code})
    assert again.status_code == 404


async def test_writes_from_unknown_origins_are_rejected(client: AsyncClient) -> None:
    await _customer_with_profile(client)
    evil = await client.post(
        "/api/v1/notifications/read-all", headers={"Origin": "https://evil.example"}
    )
    assert evil.status_code == 403

    allowed = await client.post(
        "/api/v1/notifications/read-all", headers={"Origin": "http://localhost:5173"}
    )
    assert allowed.status_code == 200


async def test_email_is_case_insensitive(client: AsyncClient) -> None:
    await register(client, CUSTOMER)
    duplicate = await client.post(
        "/api/v1/auth/register", json={**CUSTOMER, "email": CUSTOMER["email"].upper()}
    )
    assert duplicate.status_code == 409
    await login(client, CUSTOMER["email"].upper())
