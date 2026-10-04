import pytest
from httpx import AsyncClient

from tests.conftest import COACH, CUSTOMER, CUSTOMER_PROFILE, login, register

pytestmark = pytest.mark.asyncio


async def _customer(client: AsyncClient) -> None:
    await register(client, CUSTOMER)
    await login(client, CUSTOMER["email"])


async def test_registration_starts_the_history(client: AsyncClient) -> None:
    await _customer(client)
    history = (await client.get("/api/v1/measurements")).json()
    assert len(history) == 1
    assert history[0]["weight_kg"] == CUSTOMER["weight_kg"]
    assert history[0]["hip_cm"] is None


async def test_logging_updates_profile_and_metrics(client: AsyncClient) -> None:
    await _customer(client)
    await client.put("/api/v1/auth/me/customer-profile", json=CUSTOMER_PROFILE)

    logged = await client.post("/api/v1/measurements", json={"weight_kg": 80, "waist_cm": 90})
    assert logged.status_code == 201, logged.text
    assert logged.json()["height_cm"] is None

    me = (await client.get("/api/v1/auth/me")).json()
    assert me["customer"]["weight_kg"] == 80
    assert me["customer"]["waist_cm"] == 90
    assert me["customer"]["height_cm"] == CUSTOMER_PROFILE["height_cm"]

    history = (await client.get("/api/v1/measurements")).json()
    assert [entry["weight_kg"] for entry in history][-1] == 80


async def test_backdated_entry_does_not_change_profile(client: AsyncClient) -> None:
    await _customer(client)
    logged = await client.post(
        "/api/v1/measurements",
        json={"weight_kg": 95, "recorded_at": "2024-01-15T08:00:00Z"},
    )
    assert logged.status_code == 201
    me = (await client.get("/api/v1/auth/me")).json()
    assert me["customer"]["weight_kg"] == CUSTOMER["weight_kg"]

    history = (await client.get("/api/v1/measurements")).json()
    assert history[0]["weight_kg"] == 95  # oldest first


async def test_profile_edits_log_only_changed_values(client: AsyncClient) -> None:
    await _customer(client)
    await client.put(
        "/api/v1/auth/me/customer-profile", json={**CUSTOMER_PROFILE, "weight_kg": 83}
    )
    latest = (await client.get("/api/v1/measurements")).json()[-1]
    assert latest["weight_kg"] == 83
    assert latest["height_cm"] is None


@pytest.mark.parametrize(
    "payload",
    [{}, {"weight_kg": 10}, {"weight_kg": 70, "recorded_at": "2999-01-01T00:00:00Z"}],
)
async def test_invalid_logs_are_rejected(client: AsyncClient, payload: dict) -> None:
    await _customer(client)
    assert (await client.post("/api/v1/measurements", json=payload)).status_code == 422


async def test_coaches_cannot_log(client: AsyncClient) -> None:
    await register(client, COACH)
    await login(client, COACH["email"])
    assert (await client.post("/api/v1/measurements", json={"weight_kg": 70})).status_code == 403
