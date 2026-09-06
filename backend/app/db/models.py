"""SQLAlchemy models are declared here and imported by Alembic for autogeneration."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

# JSONB on Postgres, plain JSON elsewhere so the test suite can run on SQLite.
JsonList = JSONB().with_variant(JSON(), "sqlite")


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)


class User(Base):
    """Authentication record. Role decides whether a Coach or Customer row exists."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(60), nullable=False)
    last_name: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="customer")

    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    disclaimer_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    coach: Mapped["Coach | None"] = relationship(back_populates="user", uselist=False)
    customer: Mapped["Customer | None"] = relationship(back_populates="user", uselist=False)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class Coach(Base):
    __tablename__ = "coaches"

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    specialization: Mapped[str | None] = mapped_column(String(120))
    years_experience: Mapped[int | None] = mapped_column(Integer)
    bio: Mapped[str | None] = mapped_column(String(500))
    profile_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped[User] = relationship(back_populates="coach")
    # One coach has many customers.
    customers: Mapped[list["Customer"]] = relationship(back_populates="coach")


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    coach_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("coaches.id", ondelete="SET NULL"), index=True
    )
    # The customer shares this code with a coach to consent to being trained by them.
    share_code: Mapped[str] = mapped_column(String(12), unique=True, index=True, nullable=False)

    # --- Demographic ---
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(20))

    # --- Physiological ---
    height_cm: Mapped[float | None] = mapped_column(Float)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    waist_cm: Mapped[float | None] = mapped_column(Float)
    neck_cm: Mapped[float | None] = mapped_column(Float)
    hip_cm: Mapped[float | None] = mapped_column(Float)

    # --- Lifestyle & goals ---
    activity_level: Mapped[str | None] = mapped_column(String(30))
    primary_goal: Mapped[str | None] = mapped_column(String(30))
    diet_type: Mapped[str | None] = mapped_column(String(30))

    # --- Variable-length lists, stored as JSONB ---
    dietary_preferences: Mapped[list[str] | None] = mapped_column(JsonList)
    health_injury_history: Mapped[list[str] | None] = mapped_column(JsonList)

    profile_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped[User] = relationship(back_populates="customer")
    coach: Mapped[Coach | None] = relationship(back_populates="customers")
    plans: Mapped[list["WorkoutDietPlan"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )

    @property
    def age(self) -> int | None:
        if self.date_of_birth is None:
            return None
        today = date.today()
        had_birthday = (today.month, today.day) >= (
            self.date_of_birth.month,
            self.date_of_birth.day,
        )
        return today.year - self.date_of_birth.year - (0 if had_birthday else 1)


class WorkoutDietPlan(Base):
    """A workout or diet plan created by a coach for one of their customers."""

    __tablename__ = "workout_diet_plans"

    id: Mapped[uuid.UUID] = _pk()
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    coach_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("coaches.id", ondelete="CASCADE"), index=True, nullable=False
    )

    plan_type: Mapped[str] = mapped_column(String(10), nullable=False)  # "workout" | "diet"
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    content: Mapped[dict] = mapped_column(JsonList, nullable=False)
    # Customers must accept a plan before its contents are released to them.
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    customer: Mapped[Customer] = relationship(back_populates="plans")


__all__ = ["Base", "Coach", "Customer", "User", "WorkoutDietPlan"]
