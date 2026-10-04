import pytest
from httpx import AsyncClient

from tests.conftest import COACH, CUSTOMER, login, register

pytestmark = pytest.mark.asyncio


async def test_registration_rejects_weak_password(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register", json={**COACH, "password": "password"}
    )
    assert response.status_code == 422
    assert "uppercase" in response.text


async def test_registration_requires_disclaimer(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register", json={**COACH, "accepted_disclaimer": False}
    )
    assert response.status_code == 422
    assert "disclaimer" in response.text


@pytest.mark.parametrize("dob", ["2015-01-01", "1930-01-01"])
async def test_registration_enforces_age_limits(client: AsyncClient, dob: str) -> None:
    response = await client.post(
        "/api/v1/auth/register", json={**CUSTOMER, "date_of_birth": dob}
    )
    assert response.status_code == 422
    assert "18-70" in response.text


async def test_registration_signs_the_user_in(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/register", json=CUSTOMER)
    assert response.status_code == 201
    assert response.json()["email"] == CUSTOMER["email"]
    assert "httponly" in response.headers["set-cookie"].lower()

    assert (await client.get("/api/v1/auth/me")).status_code == 200


async def test_duplicate_email_rejected(client: AsyncClient) -> None:
    await register(client, CUSTOMER)
    response = await client.post("/api/v1/auth/register", json=CUSTOMER)
    assert response.status_code == 409


async def test_login_sets_httponly_cookie_and_logout_clears_it(client: AsyncClient) -> None:
    await register(client, CUSTOMER)
    await client.post("/api/v1/auth/logout")

    response = await client.post(
        "/api/v1/auth/login", json={"email": CUSTOMER["email"], "password": CUSTOMER["password"]}
    )
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert "httponly" in cookie.lower()

    assert (await client.get("/api/v1/auth/me")).status_code == 200

    await client.post("/api/v1/auth/logout")
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_wrong_password_rejected(client: AsyncClient) -> None:
    await register(client, CUSTOMER)

    response = await client.post(
        "/api/v1/auth/login", json={"email": CUSTOMER["email"], "password": "WrongPass123!"}
    )
    assert response.status_code == 401


async def test_unauthenticated_requests_rejected(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    assert (await client.get("/api/v1/coach/customers")).status_code == 401


async def test_non_session_token_rejected(client: AsyncClient) -> None:
    from app.core.security import create_token

    await register(client, CUSTOMER)
    me = (await client.get("/api/v1/auth/me")).json()
    await client.post("/api/v1/auth/logout")

    # e.g. a leftover email-verification token must never work as a session.
    token = create_token(me["id"], purpose="verify_email")
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


async def test_full_name_is_composed_and_age_derived(client: AsyncClient) -> None:
    await register(client, CUSTOMER)
    me = await login(client, CUSTOMER["email"])

    assert me["full_name"] == "Test Customer"
    assert me["customer"]["age"] >= 18
    assert me["customer"]["share_code"]
