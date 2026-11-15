"""Weekly plan review (FR-5.6) and calorie target adjustment (FR-5.7).

A review covers the seven days ending yesterday. It is created the first time it's due
(seven days after the previous review, or after the customer's first log) and the week has
enough check-ins to say something useful. Nothing is scheduled: callers run
`ensure_weekly_review` whenever the customer logs something or their coach opens them.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    BodyMeasurement,
    Coach,
    Customer,
    Notification,
    ProgressLog,
    WeeklyReview,
    WorkoutDietPlan,
)
from app.services.calculator import KCAL_PER_KG, expected_weekly_change_kg

REVIEW_DAYS = 7
MIN_LOGGED_DAYS = 3
# A weigh-in from up to a week before the period can serve as the starting weight.
WEIGHT_LOOKBACK_DAYS = 7
MIN_WEIGHT_SPAN_DAYS = 4
# Day-to-day water swings make smaller deviations meaningless.
RATE_TOLERANCE_KG = 0.25
# BRD 5.4 safety limits on the rate of change.
MAX_LOSS_KG_PER_WEEK = 1.0
MAX_GAIN_KG_PER_WEEK = 0.5
STEP_KCAL = 50
MAX_STEP_KCAL = 200
MAX_TOTAL_ADJUSTMENT_KCAL = 500
# Below this, the plan isn't really being followed, so changing it proves nothing.
MIN_MEAL_ADHERENCE = 70


def _utc(moment: datetime) -> datetime:
    # SQLite returns naive datetimes in tests; Postgres returns aware ones.
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


def _percent(part: int, whole: int) -> int | None:
    return round(part * 100 / whole) if whole else None


def clamp_total(adjustment: int) -> int:
    return max(-MAX_TOTAL_ADJUSTMENT_KCAL, min(MAX_TOTAL_ADJUSTMENT_KCAL, adjustment))


async def supersede_open_reviews(db: AsyncSession, customer: Customer) -> None:
    """Retires pending suggestions, e.g. when a newer review or a goal change replaces them."""
    await db.execute(
        update(WeeklyReview)
        .where(WeeklyReview.customer_id == customer.id, WeeklyReview.status == "open")
        .values(status="superseded", resolved_at=datetime.now(timezone.utc))
    )


async def _first_activity(db: AsyncSession, customer: Customer) -> date | None:
    first_log = await db.scalar(
        select(func.min(ProgressLog.log_date)).where(ProgressLog.customer_id == customer.id)
    )
    first_weigh_in = await db.scalar(
        select(func.min(BodyMeasurement.recorded_at)).where(
            BodyMeasurement.customer_id == customer.id
        )
    )
    days = [d for d in (first_log, _utc(first_weigh_in).date() if first_weigh_in else None) if d]
    return min(days) if days else None


async def _planned_weekdays(db: AsyncSession, customer: Customer) -> set[str] | None:
    plan = await db.scalar(
        select(WorkoutDietPlan)
        .where(
            WorkoutDietPlan.customer_id == customer.id,
            WorkoutDietPlan.plan_type == "workout",
            WorkoutDietPlan.approved_at.is_not(None),
        )
        .order_by(WorkoutDietPlan.created_at.desc())
        .limit(1)
    )
    if plan is None:
        return None
    return {day["day"] for day in plan.content.get("days", [])}


def _weight_trend(weigh_ins: list[tuple[datetime, float]], start: date, end: date) -> dict:
    """Start/end weight and the weekly rate between them, if they're far enough apart."""
    lookback_start = start - timedelta(days=WEIGHT_LOOKBACK_DAYS)
    before = [w for w in weigh_ins if lookback_start <= w[0].date() < start]
    during = [w for w in weigh_ins if start <= w[0].date() <= end]
    if not during:
        return {"start_weight_kg": None, "end_weight_kg": None, "weekly_change_kg": None}

    first = before[-1] if before else during[0]
    last = during[-1]
    span_days = (last[0] - first[0]).total_seconds() / 86400
    rate = (
        round((last[1] - first[1]) / span_days * 7, 2)
        if span_days >= MIN_WEIGHT_SPAN_DAYS
        else None
    )
    return {"start_weight_kg": first[1], "end_weight_kg": last[1], "weekly_change_kg": rate}


async def period_stats(db: AsyncSession, customer: Customer, start: date, end: date) -> dict:
    logs = (
        await db.scalars(
            select(ProgressLog).where(
                ProgressLog.customer_id == customer.id,
                ProgressLog.log_date >= start,
                ProgressLog.log_date <= end,
            )
        )
    ).all()
    measurements = (
        await db.scalars(
            select(BodyMeasurement)
            .where(
                BodyMeasurement.customer_id == customer.id,
                BodyMeasurement.weight_kg.is_not(None),
            )
            .order_by(BodyMeasurement.recorded_at)
        )
    ).all()
    weigh_ins = [(_utc(m.recorded_at), m.weight_kg) for m in measurements]

    logged_days = {log.log_date for log in logs} | {
        moment.date() for moment, _ in weigh_ins if start <= moment.date() <= end
    }

    planned_weekdays = await _planned_weekdays(db, customer)
    workout_adherence = None
    planned_sessions = trained_sessions = 0
    if planned_weekdays:
        by_date = {log.log_date: log for log in logs}
        for offset in range((end - start).days + 1):
            day = start + timedelta(days=offset)
            if day.strftime("%A") in planned_weekdays:
                planned_sessions += 1
                workout = by_date[day].workout if day in by_date else None
                if workout and workout.get("completed"):
                    trained_sessions += 1
        workout_adherence = _percent(trained_sessions, planned_sessions)

    meals = [meal for log in logs for meal in (log.meals or [])]
    followed = sum(1 for meal in meals if meal.get("status") == "followed")

    return {
        "days_logged": len(logged_days),
        "planned_sessions": planned_sessions,
        "completed_sessions": trained_sessions,
        "workout_adherence": workout_adherence,
        "meals_logged": len(meals),
        "meals_followed": followed,
        "meal_adherence": _percent(followed, len(meals)),
        "avg_mood": _average([log.mood for log in logs if log.mood is not None]),
        "avg_energy": _average([log.energy for log in logs if log.energy is not None]),
        "avg_soreness": _average([log.soreness for log in logs if log.soreness is not None]),
        "avg_sleep_hours": _average(
            [log.sleep_hours for log in logs if log.sleep_hours is not None]
        ),
        **_weight_trend(weigh_ins, start, end),
    }


def recommend_adjustment(
    goal: str, rate: float | None, meal_adherence: int | None, current_adjustment: int
) -> tuple[int, str]:
    """kcal/day to add (positive) or remove, and the reason in plain words."""
    expected = expected_weekly_change_kg(goal)
    if rate is None:
        return 0, (
            "Not enough weigh-ins to judge the calorie target. Log your weight at least twice, "
            f"{MIN_WEIGHT_SPAN_DAYS} or more days apart."
        )

    if rate < -MAX_LOSS_KG_PER_WEEK:
        raw = MAX_STEP_KCAL
        reason = (
            f"Losing {abs(rate):.2f} kg a week is faster than the safe limit of "
            f"{MAX_LOSS_KG_PER_WEEK:g} kg, so eat a little more to protect muscle."
        )
    elif rate > MAX_GAIN_KG_PER_WEEK:
        raw = -MAX_STEP_KCAL
        reason = (
            f"Gaining {rate:.2f} kg a week is faster than the {MAX_GAIN_KG_PER_WEEK:g} kg "
            "limit, so most of the extra is likely fat."
        )
    elif abs(rate - expected) <= RATE_TOLERANCE_KG:
        return 0, (
            f"Weight changed {rate:+.2f} kg this week against an expected {expected:+.2f} kg: "
            "on track, so keep the current target."
        )
    elif meal_adherence is not None and meal_adherence < MIN_MEAL_ADHERENCE:
        return 0, (
            f"Weight changed {rate:+.2f} kg against an expected {expected:+.2f} kg, but only "
            f"{meal_adherence}% of logged meals followed the plan. Follow the plan more closely "
            "before changing calories."
        )
    else:
        raw = (expected - rate) * KCAL_PER_KG / 7
        reason = (
            f"Weight changed {rate:+.2f} kg this week against an expected {expected:+.2f} kg."
        )

    step = round(raw / STEP_KCAL) * STEP_KCAL
    step = max(-MAX_STEP_KCAL, min(MAX_STEP_KCAL, step))
    # The running total from all reviews stays within the limit.
    step = clamp_total(current_adjustment + step) - current_adjustment
    if step == 0:
        return 0, reason + (
            f" The total adjustment is already at its ±{MAX_TOTAL_ADJUSTMENT_KCAL} kcal limit; "
            "review the plan together instead."
        )
    direction = "Add" if step > 0 else "Remove"
    return step, reason + f" {direction} {abs(step)} kcal a day."


def _summary(stats: dict, reason: str) -> str:
    parts = [f"{stats['days_logged']} of {REVIEW_DAYS} days logged."]
    if stats["workout_adherence"] is not None:
        parts.append(
            f"Workouts: {stats['completed_sessions']} of {stats['planned_sessions']} planned "
            f"sessions completed ({stats['workout_adherence']}%)."
        )
    if stats["meal_adherence"] is not None:
        parts.append(
            f"Meals: {stats['meals_followed']} of {stats['meals_logged']} logged meals on plan "
            f"({stats['meal_adherence']}%)."
        )
    if stats["avg_sleep_hours"] is not None:
        parts.append(f"Average sleep {stats['avg_sleep_hours']} h.")
    parts.append(reason)
    return " ".join(parts)[:1000]


async def _last_reviewed_day(db: AsyncSession, customer: Customer) -> date | None:
    """End of the last review, or the day before the customer's first log if there is none."""
    last_end = await db.scalar(
        select(func.max(WeeklyReview.period_end)).where(WeeklyReview.customer_id == customer.id)
    )
    if last_end is not None:
        return last_end
    first = await _first_activity(db, customer)
    return None if first is None else first - timedelta(days=1)


async def ensure_weekly_review(
    db: AsyncSession, customer: Customer, customer_name: str
) -> WeeklyReview | None:
    """Creates this week's review if one is due. The caller commits."""
    if not customer.profile_completed:
        return None

    yesterday = date.today() - timedelta(days=1)

    def due(last_end: date | None) -> bool:
        return last_end is not None and (yesterday - last_end).days >= REVIEW_DAYS

    if not due(await _last_reviewed_day(db, customer)):
        return None
    # Two requests can arrive together (two tabs, or the coach and customer at once). Lock the
    # customer and check again, so only one of them creates the review.
    await db.execute(select(Customer.id).where(Customer.id == customer.id).with_for_update())
    if not due(await _last_reviewed_day(db, customer)):
        return None

    start = yesterday - timedelta(days=REVIEW_DAYS - 1)
    stats = await period_stats(db, customer, start, yesterday)
    if stats["days_logged"] < MIN_LOGGED_DAYS:
        return None

    goal = customer.primary_goal or "maintain"
    adjustment, reason = recommend_adjustment(
        goal, stats["weekly_change_kg"], stats["meal_adherence"], customer.calorie_adjustment or 0
    )
    stats["expected_weekly_change_kg"] = expected_weekly_change_kg(goal)
    stats["goal"] = goal

    # Only the newest recommendation can be applied.
    await supersede_open_reviews(db, customer)
    review = WeeklyReview(
        customer_id=customer.id,
        period_start=start,
        period_end=yesterday,
        stats=stats,
        summary=_summary(stats, reason),
        recommended_adjustment=adjustment,
        status="open" if adjustment else "none",
    )
    db.add(review)

    period = f"{start:%d %b} – {yesterday:%d %b}"
    db.add(
        Notification(
            user_id=customer.user_id, message=f"Your weekly review for {period} is ready."
        )
    )
    if customer.coach_id is not None:
        coach_user_id = await db.scalar(select(Coach.user_id).where(Coach.id == customer.coach_id))
        suggestion = f" It suggests {adjustment:+d} kcal a day." if adjustment else ""
        db.add(
            Notification(
                user_id=coach_user_id,
                message=f"{customer_name}'s weekly review for {period} is ready.{suggestion}",
            )
        )
    return review


def apply_review(review: WeeklyReview, customer: Customer) -> int:
    """Adds the recommendation to the customer's calorie target. Returns the new total."""
    customer.calorie_adjustment = clamp_total(
        (customer.calorie_adjustment or 0) + review.recommended_adjustment
    )
    review.status = "applied"
    review.resolved_at = datetime.now(timezone.utc)
    return customer.calorie_adjustment
