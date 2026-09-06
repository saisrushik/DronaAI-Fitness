import os
from collections.abc import AsyncGenerator

# Tests run against a throwaway SQLite database, never the real one.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-tests-only")
os.environ.setdefault("SMTP_HOST", "")

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import update  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.db.models import User  # noqa: E402
from app.db.session import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

CUSTOMER = {
    "first_name": "Test",
    "last_name": "Customer",
    "email": "customer@test.com",
    "password": "Password123!",
    "role": "customer",
    "accepted_disclaimer": True,
    "date_of_birth": "1994-03-15",
    "gender": "male",
    "height_cm": 180,
    "weight_kg": 85,
    "waist_cm": 94,
    "neck_cm": 40,
}

COACH = {
    "first_name": "Test",
    "last_name": "Coach",
    "email": "coach@test.com",
    "password": "Password123!",
    "role": "coach",
    "accepted_disclaimer": True,
}

CUSTOMER_PROFILE = {
    "height_cm": 180,
    "weight_kg": 85,
    "waist_cm": 94,
    "neck_cm": 40,
    "activity_level": "moderate",
    "primary_goal": "lose_fat",
    "diet_type": "non_vegetarian",
    "dietary_preferences": [],
    "health_injury_history": [],
}


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db() -> AsyncGenerator:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.limiter.reset()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        async_client.session_factory = session_factory  # type: ignore[attr-defined]
        yield async_client

    app.dependency_overrides.clear()
    await engine.dispose()


async def register_verified(client: AsyncClient, payload: dict) -> None:
    """Registers an account and marks it verified, skipping the email round-trip."""
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text

    async with client.session_factory() as session:  # type: ignore[attr-defined]
        await session.execute(
            update(User).where(User.email == payload["email"]).values(email_verified=True)
        )
        await session.commit()


async def login(client: AsyncClient, email: str, password: str = "Password123!") -> dict:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()
