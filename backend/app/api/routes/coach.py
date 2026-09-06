import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_coach
from app.db.models import Coach, Customer, WorkoutDietPlan
from app.db.session import get_db
from app.schemas.user import (
    CustomerDetail,
    CustomerSummary,
    GeneratePlanRequest,
    LinkCustomerRequest,
    PlanResponse,
)
from app.services.calculator import calculate_bmi
from app.services.metrics import metrics_for
from app.services.plan_generator import generate_diet_plan, generate_workout_plan

router = APIRouter(prefix="/coach", tags=["coach"])


def _summary(customer: Customer) -> CustomerSummary:
    bmi = (
        calculate_bmi(customer.weight_kg, customer.height_cm)
        if customer.weight_kg and customer.height_cm
        else None
    )
    return CustomerSummary(
        id=customer.id,
        full_name=customer.user.full_name,
        email=customer.user.email,
        profile_completed=customer.profile_completed,
        date_of_birth=customer.date_of_birth,
        age=customer.age,
        gender=customer.gender,
        height_cm=customer.height_cm,
        weight_kg=customer.weight_kg,
        waist_cm=customer.waist_cm,
        neck_cm=customer.neck_cm,
        hip_cm=customer.hip_cm,
        activity_level=customer.activity_level,
        primary_goal=customer.primary_goal,
        diet_type=customer.diet_type,
        dietary_preferences=customer.dietary_preferences,
        health_injury_history=customer.health_injury_history,
        bmi=bmi,
        workout_plan_count=sum(1 for p in customer.plans if p.plan_type == "workout"),
        diet_plan_count=sum(1 for p in customer.plans if p.plan_type == "diet"),
    )


async def _load_customer(db: AsyncSession, customer_id: uuid.UUID) -> Customer:
    result = await db.execute(
        select(Customer)
        .where(Customer.id == customer_id)
        .options(selectinload(Customer.user), selectinload(Customer.plans))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return customer


async def _load_my_customer(
    db: AsyncSession, coach: Coach, customer_id: uuid.UUID
) -> Customer:
    customer = await _load_customer(db, customer_id)
    if customer.coach_id != coach.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This customer is not assigned to you")
    return customer


@router.get("/customers", response_model=list[CustomerSummary])
async def list_my_customers(
    coach: Coach = Depends(get_current_coach), db: AsyncSession = Depends(get_db)
) -> list[CustomerSummary]:
    result = await db.execute(
        select(Customer)
        .where(Customer.coach_id == coach.id)
        .options(selectinload(Customer.user), selectinload(Customer.plans))
        .order_by(Customer.id)
    )
    return [_summary(c) for c in result.scalars().all()]


@router.post("/customers/link", response_model=CustomerSummary)
async def link_customer(
    payload: LinkCustomerRequest,
    coach: Coach = Depends(get_current_coach),
    db: AsyncSession = Depends(get_db),
) -> CustomerSummary:
    """Adds a customer using the share code they gave the coach. This is the consent step."""
    result = await db.execute(
        select(Customer)
        .where(Customer.share_code == payload.share_code.strip().upper())
        .options(selectinload(Customer.user), selectinload(Customer.plans))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No customer found with that share code")
    if customer.coach_id == coach.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "This customer is already on your roster")
    if customer.coach_id is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This customer already has a coach")

    customer.coach_id = coach.id
    await db.commit()
    return _summary(await _load_customer(db, customer.id))


@router.get("/customers/{customer_id}", response_model=CustomerDetail)
async def get_customer(
    customer_id: uuid.UUID,
    coach: Coach = Depends(get_current_coach),
    db: AsyncSession = Depends(get_db),
) -> CustomerDetail:
    customer = await _load_my_customer(db, coach, customer_id)

    return CustomerDetail(
        **_summary(customer).model_dump(),
        metrics=metrics_for(customer),
        plans=sorted(customer.plans, key=lambda p: p.created_at, reverse=True),
    )


@router.post("/customers/{customer_id}/plans", response_model=PlanResponse, status_code=201)
async def generate_plan(
    customer_id: uuid.UUID,
    payload: GeneratePlanRequest,
    coach: Coach = Depends(get_current_coach),
    db: AsyncSession = Depends(get_db),
) -> WorkoutDietPlan:
    customer = await _load_my_customer(db, coach, customer_id)
    if not customer.profile_completed:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Customer must complete their profile before a plan can be generated",
        )

    if payload.plan_type == "workout":
        content = generate_workout_plan(customer)
        title = f"{content['days_per_week']}-day workout plan"
    else:
        content = generate_diet_plan(customer)
        title = f"Weekly diet plan — {content['targets']['target_calories']} kcal/day"

    plan = WorkoutDietPlan(
        customer_id=customer.id,
        coach_id=coach.id,
        plan_type=payload.plan_type,
        title=title,
        content=content,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan
