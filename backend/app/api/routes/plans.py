from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_current_customer, get_current_user
from app.db.models import Coach, Customer, Notification, User, WorkoutDietPlan
from app.db.session import get_db
from app.schemas.user import MessageResponse, PlanResponse
from app.services.coaching import end_coaching

router = APIRouter(prefix="/plans", tags=["plans"])


def _visible(plan: WorkoutDietPlan) -> PlanResponse:
    """Plan contents are withheld until the customer approves the plan."""
    return PlanResponse(
        id=plan.id,
        customer_id=plan.customer_id,
        coach_id=plan.coach_id,
        plan_type=plan.plan_type,
        title=plan.title,
        content=plan.content if plan.approved_at else None,
        approved_at=plan.approved_at,
        created_at=plan.created_at,
    )


@router.get("/mine", response_model=list[PlanResponse])
async def my_plans(
    customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_db)
) -> list[PlanResponse]:
    result = await db.execute(
        select(WorkoutDietPlan)
        .where(WorkoutDietPlan.customer_id == customer.id)
        .order_by(WorkoutDietPlan.created_at.desc())
    )
    return [_visible(plan) for plan in result.scalars().all()]


@router.post("/{plan_id}/approve", response_model=PlanResponse)
async def approve_plan(
    plan_id: UUID,
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> PlanResponse:
    plan = await db.get(WorkoutDietPlan, plan_id)
    if plan is None or plan.customer_id != customer.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan not found")

    if plan.approved_at is None:
        plan.approved_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(plan)

    return _visible(plan)


@router.get("/my-coach")
async def my_coach(
    customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_db)
) -> dict | None:
    if customer.coach_id is None:
        return None

    result = await db.execute(
        select(Coach).where(Coach.id == customer.coach_id).options(joinedload(Coach.user))
    )
    coach = result.scalar_one()
    return {
        "full_name": coach.user.full_name,
        "email": coach.user.email,
        "specialization": coach.specialization,
        "years_experience": coach.years_experience,
        "bio": coach.bio,
    }


@router.post("/my-coach/leave", response_model=MessageResponse)
async def leave_coach(
    user: User = Depends(get_current_user),
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """The customer withdraws their coach's access. They can then share their code with another."""
    if customer.coach_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You don't have a coach")

    coach_id = customer.coach_id
    coach_user_id = await db.scalar(select(Coach.user_id).where(Coach.id == coach_id))
    await end_coaching(db, customer, coach_id, "Closed because the customer left coaching.")
    db.add(
        Notification(user_id=coach_user_id, message=f"{user.full_name} left your roster.")
    )
    await db.commit()
    return MessageResponse(
        message="You left your coach. Share your code with a new coach to continue."
    )
