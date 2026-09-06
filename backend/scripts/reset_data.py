"""Delete all seeded data so `python -m scripts.seed` can rebuild it. Dev use only."""

import asyncio

from sqlalchemy import delete

from app.db.models import Coach, Customer, User, WorkoutDietPlan
from app.db.session import AsyncSessionLocal


async def reset() -> None:
    async with AsyncSessionLocal() as db:
        for model in (WorkoutDietPlan, Customer, Coach, User):
            await db.execute(delete(model))
        await db.commit()
    print("All users, coaches, customers and plans deleted.")


if __name__ == "__main__":
    asyncio.run(reset())
