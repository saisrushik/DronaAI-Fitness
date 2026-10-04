"""Insert dummy coaches and customers. Run with: python -m scripts.seed"""

import asyncio
from datetime import date, datetime, timezone

from sqlalchemy import select

from app.core.config import settings
from app.core.security import generate_share_code, hash_password
from app.db.models import Coach, Customer, User, WorkoutDietPlan
from app.db.session import AsyncSessionLocal
from app.services.plan_generator import generate_diet_plan, generate_workout_plan

PASSWORD = "Password123!"

COACHES = [
    {
        "email": "coach.maria@example.com",
        "first_name": "Maria",
        "last_name": "Lopez",
        "specialization": "Strength & conditioning",
        "years_experience": 12,
        "bio": "Former competitive powerlifter helping clients build strength safely.",
    },
    {
        "email": "coach.raj@example.com",
        "first_name": "Raj",
        "last_name": "Patel",
        "specialization": "Endurance & weight loss",
        "years_experience": 7,
        "bio": "Marathon coach focused on sustainable fat loss and running performance.",
    },
]

# coach_email links each customer to their coach (one coach, many customers).
CUSTOMERS = [
    {
        "email": "alex@example.com",
        "first_name": "Alex",
        "last_name": "Doe",
        "coach_email": "coach.maria@example.com",
        "date_of_birth": date(1998, 4, 12),
        "gender": "male",
        "height_cm": 178.0,
        "weight_kg": 82.5,
        "waist_cm": 92.0,
        "neck_cm": 39.0,
        "activity_level": "moderate",
        "primary_goal": "lose_fat",
        "diet_type": "non_vegetarian",
        "dietary_preferences": ["no dairy"],
        "health_injury_history": ["lower back pain"],
        "profile_completed": True,
    },
    {
        "email": "priya@example.com",
        "first_name": "Priya",
        "last_name": "Sharma",
        "coach_email": "coach.maria@example.com",
        "date_of_birth": date(1992, 9, 3),
        "gender": "female",
        "height_cm": 163.0,
        "weight_kg": 58.0,
        "waist_cm": 72.0,
        "neck_cm": 32.0,
        "hip_cm": 96.0,
        "activity_level": "active",
        "primary_goal": "build_muscle",
        "diet_type": "vegetarian",
        "dietary_preferences": ["peanut allergy"],
        "health_injury_history": [],
        "profile_completed": True,
    },
    {
        "email": "diego@example.com",
        "first_name": "Diego",
        "last_name": "Fernandez",
        "coach_email": "coach.maria@example.com",
        "date_of_birth": date(1981, 1, 25),
        "gender": "male",
        "height_cm": 172.0,
        "weight_kg": 95.0,
        "waist_cm": 106.0,
        "neck_cm": 42.0,
        "activity_level": "sedentary",
        "primary_goal": "lose_fat",
        "diet_type": "eggetarian",
        "dietary_preferences": [],
        "health_injury_history": ["knee surgery"],
        "profile_completed": True,
    },
    {
        "email": "lena@example.com",
        "first_name": "Lena",
        "last_name": "Novak",
        "coach_email": "coach.raj@example.com",
        "date_of_birth": date(1996, 6, 18),
        "gender": "female",
        "height_cm": 168.0,
        "weight_kg": 61.0,
        "waist_cm": 70.0,
        "neck_cm": 31.0,
        "hip_cm": 94.0,
        "activity_level": "very_active",
        "primary_goal": "improve_endurance",
        "diet_type": "vegan",
        "dietary_preferences": [],
        "health_injury_history": [],
        "profile_completed": True,
    },
    # No coach yet, and goals not filled in — good for testing the first-login flow.
    {
        "email": "sam@example.com",
        "first_name": "Sam",
        "last_name": "Taylor",
        "coach_email": None,
        "date_of_birth": date(1995, 11, 8),
        "gender": "male",
        "height_cm": 175.0,
        "weight_kg": 74.0,
        "waist_cm": 84.0,
        "neck_cm": 37.0,
        "profile_completed": False,
    },
]

MEASUREMENT_FIELDS = (
    "date_of_birth",
    "gender",
    "height_cm",
    "weight_kg",
    "waist_cm",
    "neck_cm",
    "hip_cm",
    "activity_level",
    "primary_goal",
    "diet_type",
    "dietary_preferences",
    "health_injury_history",
)


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        known = set((await db.execute(select(User.email))).scalars().all())

        coach_by_email: dict[str, Coach] = {}
        for data in COACHES:
            if data["email"] in known:
                print(f"skip   {data['email']}")
                continue
            user = User(
                email=data["email"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                role="coach",
                disclaimer_accepted_at=datetime.now(timezone.utc),
                password_hash=hash_password(PASSWORD),
            )
            db.add(user)
            await db.flush()
            coach = Coach(
                user_id=user.id,
                specialization=data["specialization"],
                years_experience=data["years_experience"],
                bio=data["bio"],
                profile_completed=True,
            )
            db.add(coach)
            await db.flush()
            coach_by_email[data["email"]] = coach
            print(f"coach  {data['email']}")

        for data in CUSTOMERS:
            if data["email"] in known:
                print(f"skip   {data['email']}")
                continue
            user = User(
                email=data["email"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                role="customer",
                disclaimer_accepted_at=datetime.now(timezone.utc),
                password_hash=hash_password(PASSWORD),
            )
            db.add(user)
            await db.flush()

            coach = coach_by_email.get(data["coach_email"]) if data["coach_email"] else None
            customer = Customer(
                user_id=user.id,
                coach_id=coach.id if coach else None,
                share_code=generate_share_code(),
                profile_completed=data["profile_completed"],
                **{field: data.get(field) for field in MEASUREMENT_FIELDS},
            )
            db.add(customer)
            await db.flush()
            print(f"cust   {data['email']} -> {data['coach_email'] or 'no coach'} "
                  f"(code {customer.share_code})")

            # Give assigned customers a starter plan from their coach.
            # The workout is pre-approved; the diet is left pending to show the approval step.
            if coach and customer.profile_completed:
                workout = generate_workout_plan(customer)
                diet = generate_diet_plan(customer)
                db.add(
                    WorkoutDietPlan(
                        customer_id=customer.id,
                        coach_id=coach.id,
                        plan_type="workout",
                        title=f"{workout['days_per_week']}-day workout plan",
                        content=workout,
                        approved_at=datetime.now(timezone.utc),
                    )
                )
                db.add(
                    WorkoutDietPlan(
                        customer_id=customer.id,
                        coach_id=coach.id,
                        plan_type="diet",
                        title=f"Weekly diet plan — {diet['targets']['target_calories']} kcal/day",
                        content=diet,
                    )
                )

        await db.commit()

    print(f"\nDone. All dummy accounts share the password: {PASSWORD}")


if __name__ == "__main__":
    if settings.is_production:
        raise SystemExit("Refusing to seed: demo accounts share a published password.")
    asyncio.run(seed())
