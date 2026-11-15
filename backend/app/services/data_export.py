"""Everything stored about a user, as one JSON document (GDPR right of access/portability)."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AuthSession,
    BodyMeasurement,
    Coach,
    CustomerRequest,
    Notification,
    ProgressLog,
    User,
    WeeklyReview,
    WorkoutDietPlan,
)
from app.services.metrics import metrics_for


def _row(obj: object, exclude: tuple[str, ...] = ()) -> dict:
    return {
        column.key: getattr(obj, column.key)
        for column in obj.__table__.columns  # type: ignore[attr-defined]
        if column.key not in exclude
    }


async def build_export(db: AsyncSession, user: User) -> dict:
    data: dict = {
        "exported_at": datetime.now(timezone.utc),
        "account": _row(user, exclude=("password_hash",)),
    }

    sessions = await db.scalars(
        select(AuthSession).where(AuthSession.user_id == user.id).order_by(AuthSession.created_at)
    )
    data["sign_in_sessions"] = [
        _row(s, exclude=("refresh_jti", "previous_jti")) for s in sessions.all()
    ]

    notifications = await db.scalars(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at)
    )
    data["notifications"] = [_row(n) for n in notifications.all()]

    if user.coach is not None:
        # Customers' plans and health data belong to them, not to the coach.
        data["coach_profile"] = _row(user.coach)

    customer = user.customer
    if customer is None:
        return data

    data["customer_profile"] = {**_row(customer), "age": customer.age}
    data["health_metrics"] = metrics_for(customer)

    data["coach"] = None
    if customer.coach_id is not None:
        coach_user = await db.scalar(
            select(User).join(Coach, Coach.user_id == User.id).where(Coach.id == customer.coach_id)
        )
        if coach_user is not None:
            data["coach"] = {"full_name": coach_user.full_name, "email": coach_user.email}

    plans = await db.scalars(
        select(WorkoutDietPlan)
        .where(WorkoutDietPlan.customer_id == customer.id)
        .order_by(WorkoutDietPlan.created_at)
    )
    # Same rule as the app: a plan's contents are released only once the customer accepts it.
    data["plans"] = [
        {**_row(p), "content": p.content if p.approved_at else None} for p in plans.all()
    ]

    measurements = await db.scalars(
        select(BodyMeasurement)
        .where(BodyMeasurement.customer_id == customer.id)
        .order_by(BodyMeasurement.recorded_at)
    )
    data["body_measurements"] = [_row(m) for m in measurements.all()]

    logs = await db.scalars(
        select(ProgressLog)
        .where(ProgressLog.customer_id == customer.id)
        .order_by(ProgressLog.log_date)
    )
    data["progress_logs"] = [_row(log) for log in logs.all()]

    reviews = await db.scalars(
        select(WeeklyReview)
        .where(WeeklyReview.customer_id == customer.id)
        .order_by(WeeklyReview.period_start)
    )
    data["weekly_reviews"] = [_row(r) for r in reviews.all()]

    requests = await db.scalars(
        select(CustomerRequest)
        .where(CustomerRequest.customer_id == customer.id)
        .order_by(CustomerRequest.created_at)
    )
    data["requests"] = [_row(r) for r in requests.all()]

    return data
