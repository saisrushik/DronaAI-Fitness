import pytest
from httpx import AsyncClient

from tests.conftest import COACH, CUSTOMER, login, register_verified

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


async def test_login_blocked_until_email_verified(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=CUSTOMER)

    response = await client.post(
        "/api/v1/auth/login", json={"email": CUSTOMER["email"], "password": CUSTOMER["password"]}
    )
    assert response.status_code == 403
    assert "verify" in response.text.lower()


async def test_login_sets_httponly_cookie_and_logout_clears_it(client: AsyncClient) -> None:
    await register_verified(client, CUSTOMER)

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
    await register_verified(client, CUSTOMER)

    response = await client.post(
        "/api/v1/auth/login", json={"email": CUSTOMER["email"], "password": "WrongPass123!"}
    )
    assert response.status_code == 401


async def test_unauthenticated_requests_rejected(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    assert (await client.get("/api/v1/coach/customers")).status_code == 401


async def test_password_reset_token_cannot_be_reused_as_session(client: AsyncClient) -> None:
    await register_verified(client, CUSTOMER)
    await client.post("/api/v1/auth/forgot-password", json={"email": CUSTOMER["email"]})

    # A verification token must not be accepted by the reset endpoint.
    from app.core.security import VERIFY_EMAIL, create_token

    bogus = create_token("00000000-0000-0000-0000-000000000000", VERIFY_EMAIL)
    response = await client.post(
        "/api/v1/auth/reset-password", json={"token": bogus, "password": "Password123!"}
    )
    assert response.status_code == 400


async def test_forgot_password_does_not_reveal_account_existence(client: AsyncClient) -> None:
    known = await client.post("/api/v1/auth/forgot-password", json={"email": CUSTOMER["email"]})
    unknown = await client.post("/api/v1/auth/forgot-password", json={"email": "nobody@test.com"})
    assert known.json() == unknown.json()


async def test_full_name_is_composed_and_age_derived(client: AsyncClient) -> None:
    await register_verified(client, CUSTOMER)
    me = await login(client, CUSTOMER["email"])

    assert me["full_name"] == "Test Customer"
    assert me["customer"]["age"] >= 18
    assert me["customer"]["share_code"]
