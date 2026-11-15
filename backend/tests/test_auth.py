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


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_logout_revokes_the_access_token_server_side(client: AsyncClient) -> None:
    await register(client, CUSTOMER)
    stolen = client.cookies.get("fitness_session")

    await client.post("/api/v1/auth/logout")
    response = await client.get("/api/v1/auth/me", headers=_bearer(stolen))
    assert response.status_code == 401


async def test_refresh_rotates_tokens_and_detects_replay(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from datetime import timedelta

    from app.services import auth_sessions

    monkeypatch.setattr(auth_sessions, "REUSE_GRACE", timedelta(0))
    await register(client, CUSTOMER)
    old_refresh = client.cookies.get("fitness_refresh")

    refreshed = await client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200
    assert client.cookies.get("fitness_refresh") != old_refresh
    current_access = client.cookies.get("fitness_session")
    assert (await client.get("/api/v1/auth/me")).status_code == 200

    # Someone replays the refresh token that was already used.
    client.cookies.clear()
    replay = await client.post(
        "/api/v1/auth/refresh", headers={"Cookie": f"fitness_refresh={old_refresh}"}
    )
    assert replay.status_code == 401
    # The whole session is ended, including the legitimate user's newer tokens.
    assert (await client.get("/api/v1/auth/me", headers=_bearer(current_access))).status_code == 401


async def test_parallel_refresh_with_previous_token_is_tolerated(client: AsyncClient) -> None:
    await register(client, CUSTOMER)
    old_refresh = client.cookies.get("fitness_refresh")
    assert (await client.post("/api/v1/auth/refresh")).status_code == 200

    # A second tab refreshing with the token that was rotated a moment ago.
    client.cookies.clear()
    second_tab = await client.post(
        "/api/v1/auth/refresh", headers={"Cookie": f"fitness_refresh={old_refresh}"}
    )
    assert second_tab.status_code == 200
    assert (await client.get("/api/v1/auth/me")).status_code == 200


async def test_refresh_without_a_session_clears_cookies(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401
    assert "fitness_session" in response.headers.get("set-cookie", "")


async def test_logout_everywhere_ends_other_devices(client: AsyncClient) -> None:
    await register(client, CUSTOMER)
    laptop = client.cookies.get("fitness_session")

    client.cookies.clear()
    await login(client, CUSTOMER["email"])
    phone = client.cookies.get("fitness_session")
    # Only bearer tokens from here on, so the jar's cookie can't stand in for either device.
    client.cookies.clear()
    assert (await client.get("/api/v1/auth/me", headers=_bearer(laptop))).status_code == 200

    response = await client.post("/api/v1/auth/logout-all", headers=_bearer(phone))
    assert response.status_code == 200
    assert (await client.get("/api/v1/auth/me", headers=_bearer(laptop))).status_code == 401
    assert (await client.get("/api/v1/auth/me", headers=_bearer(phone))).status_code == 401
