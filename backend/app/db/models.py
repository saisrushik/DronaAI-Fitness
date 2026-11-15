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
    UniqueConstraint,
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
    # "metric" or "imperial". Only changes how values are shown and entered; storage is metric.
    unit_system: Mapped[str] = mapped_column(
        String(10), nullable=False, default="metric", server_default="metric"
    )

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
    gender: Mapped[str | None] = mapped_column(String(20))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
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
    # ISO 3166-1 alpha-2. India uses the Asian BMI cut-offs as its primary standard.
    country: Mapped[str] = mapped_column(
        String(2), nullable=False, default="IN", server_default="IN"
    )

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
    budget_level: Mapped[str | None] = mapped_column(String(10))
    stress_level: Mapped[str | None] = mapped_column(String(10))

    # --- Workout preferences ---
    training_experience: Mapped[str | None] = mapped_column(String(20))
    training_location: Mapped[str | None] = mapped_column(String(10))
    training_days_per_week: Mapped[int | None] = mapped_column(Integer)

    # --- Variable-length lists, stored as JSONB ---
    dietary_preferences: Mapped[list[str] | None] = mapped_column(JsonList)
    medical_conditions: Mapped[list[str] | None] = mapped_column(JsonList)
    # [{"body_part", "severity", "recovery_status", "date_of_injury", "notes"}]
    injuries: Mapped[list[dict] | None] = mapped_column(JsonList)

    profile_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Set when a completed profile changes, so the coach can tell which plans are out of date.
    profile_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # kcal/day the coach added or removed after weekly reviews (FR-5.7). Reset on goal change.
    calorie_adjustment: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    user: Mapped[User] = relationship(back_populates="customer")
    coach: Mapped[Coach | None] = relationship(back_populates="customers")
    plans: Mapped[list["WorkoutDietPlan"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    requests: Mapped[list["CustomerRequest"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    measurements: Mapped[list["BodyMeasurement"]] = relationship(
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
    # Cleared if the coach deletes their account; the customer keeps the plan.
    coach_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("coaches.id", ondelete="SET NULL"), index=True
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


class CustomerRequest(Base):
    """Something a customer asks of their coach: a meal swap, workout change, injury or question."""

    __tablename__ = "customer_requests"

    id: Mapped[uuid.UUID] = _pk()
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Cleared if the coach deletes their account; the customer keeps their request history.
    coach_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("coaches.id", ondelete="SET NULL"), index=True
    )
    # Only meal requests point at a plan.
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workout_diet_plans.id", ondelete="CASCADE"), index=True
    )

    request_type: Mapped[str] = mapped_column(String(10), nullable=False)  # meal|workout|injury|query
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="pending")
    description: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    # Meal requests: [{"day", "session", "items": ["food name", ...]}]
    requested_meals: Mapped[list | None] = mapped_column(JsonList)
    # Same shape, but each item carries quantity, calories and macros set by the coach.
    approved_meals: Mapped[list | None] = mapped_column(JsonList)
    coach_note: Mapped[str] = mapped_column(String(500), nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    customer: Mapped[Customer] = relationship(back_populates="requests")
    plan: Mapped[WorkoutDietPlan | None] = relationship()


class BodyMeasurement(Base):
    """One logged set of body measurements. Fields the customer didn't measure stay empty."""

    __tablename__ = "body_measurements"

    id: Mapped[uuid.UUID] = _pk()
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    height_cm: Mapped[float | None] = mapped_column(Float)
    waist_cm: Mapped[float | None] = mapped_column(Float)
    neck_cm: Mapped[float | None] = mapped_column(Float)
    hip_cm: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    customer: Mapped[Customer] = relationship(back_populates="measurements")


class ProgressLog(Base):
    """A customer's daily check-in: workout done, meals eaten and how they felt."""

    __tablename__ = "progress_logs"
    __table_args__ = (UniqueConstraint("customer_id", "log_date"),)

    id: Mapped[uuid.UUID] = _pk()
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    # {"completed", "plan_day", "exercises": [{"name", "sets", "reps", "weight_kg"}]}
    workout: Mapped[dict | None] = mapped_column(JsonList)
    # [{"session", "status": "followed" | "other" | "skipped", "note"}]
    meals: Mapped[list | None] = mapped_column(JsonList)
    mood: Mapped[int | None] = mapped_column(Integer)
    energy: Mapped[int | None] = mapped_column(Integer)
    soreness: Mapped[int | None] = mapped_column(Integer)
    sleep_hours: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customer_requests.id", ondelete="CASCADE")
    )
    message: Mapped[str] = mapped_column(String(300), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WeeklyReview(Base):
    """A look back over one week of check-ins and weigh-ins (FR-5.6), with an optional
    calorie adjustment for the coach to apply (FR-5.7)."""

    __tablename__ = "weekly_reviews"
    # Backstop for the per-customer lock in services/weekly_review: one review per week.
    __table_args__ = (UniqueConstraint("customer_id", "period_end"),)

    id: Mapped[uuid.UUID] = _pk()
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    # Adherence, wellness averages, weight trend and expected rate; see services/weekly_review.
    stats: Mapped[dict] = mapped_column(JsonList, nullable=False)
    summary: Mapped[str] = mapped_column(String(1000), nullable=False)
    recommended_adjustment: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # open | applied | dismissed | superseded (a newer review replaced it) | none (nothing to do)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="open")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AuthSession(Base):
    """One signed-in browser or device. Revoking it ends both its access and refresh tokens."""

    __tablename__ = "auth_sessions"

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # The refresh token currently valid for this session. Rotated on every refresh.
    refresh_jti: Mapped[str] = mapped_column(String(64), nullable=False)
    # The token it replaced, still honoured briefly so parallel tabs refreshing at once don't
    # look like a stolen token being replayed.
    previous_jti: Mapped[str | None] = mapped_column(String(64))
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


__all__ = [
    "AuthSession",
    "Base",
    "BodyMeasurement",
    "Coach",
    "Customer",
    "CustomerRequest",
    "Notification",
    "ProgressLog",
    "User",
    "WeeklyReview",
    "WorkoutDietPlan",
]
