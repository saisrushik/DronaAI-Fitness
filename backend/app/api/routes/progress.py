import calendar
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_customer
from app.db.models import Customer, ProgressLog, WorkoutDietPlan
from app.db.session import get_db
from app.schemas.user import ExerciseToggle, ProgressLogResponse, ProgressLogUpsert

router = APIRouter(prefix="/progress", tags=["progress"])


def _check_date(log_date: date) -> None:
    # One day of slack covers customers in time zones ahead of the server.
    if log_date > date.today() + timedelta(days=1):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can't log a day in the future")
    if log_date < date.today() - timedelta(days=366):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Logs older than a year can't be changed")


async def _planned_day(db: AsyncSession, customer: Customer, log_date: date) -> dict | None:
    """The day of the customer's latest accepted workout plan that falls on this weekday."""
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
    weekday = calendar.day_name[log_date.weekday()]
    return next((d for d in plan.content.get("days", []) if d["day"] == weekday), None)


async def _get_or_create(db: AsyncSession, customer: Customer, log_date: date) -> ProgressLog:
    log = await db.scalar(
        select(ProgressLog).where(
            ProgressLog.customer_id == customer.id, ProgressLog.log_date == log_date
        )
    )
    if log is None:
        log = ProgressLog(customer_id=customer.id, log_date=log_date, notes="")
        db.add(log)
    return log


def _set_workout(log: ProgressLog, planned: dict | None, done: list[str], activities: list) -> None:
    """Stores what was done and whether it covers the whole planned session."""
    planned_names = [e["name"] for e in planned["exercises"]] if planned else []
    if planned_names:
        done = [name for name in done if name in planned_names]
    if not done and not activities:
        log.workout = None
        return
    completed = (
        all(name in done for name in planned_names) if planned_names else True
    )
    log.workout = {
        "plan_day": planned["day"] if planned else None,
        "completed": completed,
        "exercises": [{"name": name, "done": True} for name in done],
        "activities": activities,
    }


def _done_names(log: ProgressLog) -> list[str]:
    return [e["name"] for e in (log.workout or {}).get("exercises", []) if e.get("done")]


@router.get("", response_model=list[ProgressLogResponse])
async def my_progress(
    days: int = Query(default=90, ge=1, le=366),
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> list[ProgressLog]:
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(ProgressLog)
        .where(ProgressLog.customer_id == customer.id, ProgressLog.log_date >= since)
        .order_by(ProgressLog.log_date)
    )
    return list(result.scalars().all())


@router.put("/{log_date}", response_model=ProgressLogResponse)
async def save_progress(
    log_date: date,
    payload: ProgressLogUpsert,
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> ProgressLog:
    """Creates or replaces the check-in for one day, keeping exercises ticked on the plan."""
    _check_date(log_date)
    log = await _get_or_create(db, customer, log_date)
    planned = await _planned_day(db, customer, log_date)

    data = payload.model_dump()
    _set_workout(log, planned, _done_names(log), data["activities"])
    log.meals = data["meals"]
    log.mood = payload.mood
    log.energy = payload.energy
    log.soreness = payload.soreness
    log.sleep_hours = payload.sleep_hours
    log.notes = payload.notes.strip()
    await db.commit()
    await db.refresh(log)
    return log


@router.post("/{log_date}/exercises", response_model=ProgressLogResponse)
async def toggle_exercise(
    log_date: date,
    payload: ExerciseToggle,
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> ProgressLog:
    """Ticks a plan exercise on or off for a day; the rest of the check-in is untouched."""
    _check_date(log_date)
    planned = await _planned_day(db, customer, log_date)
    if planned is None or payload.name not in [e["name"] for e in planned["exercises"]]:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"{payload.name} isn't in your plan for this day"
        )

    log = await _get_or_create(db, customer, log_date)
    done = [name for name in _done_names(log) if name != payload.name]
    if payload.done:
        done.append(payload.name)
    activities = (log.workout or {}).get("activities", [])
    _set_workout(log, planned, done, activities)
    await db.commit()
    await db.refresh(log)
    return log
