import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.api.deps import get_current_coach, get_current_user
from app.core.rate_limit import LOGIN_LIMIT, limiter
from app.core.security import generate_share_code
from app.db.models import Coach, Customer, Notification, User, WeeklyReview, WorkoutDietPlan
from app.db.session import get_db
from app.schemas.user import (
    CustomerDetail,
    CustomerSummary,
    GeneratePlanRequest,
    LinkCustomerRequest,
    MealUpdate,
    MessageResponse,
    PlanResponse,
    WeeklyReviewResponse,
)
from app.services.calculator import calculate_bmi
from app.services.coaching import end_coaching
from app.services.metrics import metrics_for
from app.services.weekly_review import apply_review, ensure_weekly_review
from app.services.plan_generator import (
    apply_meal_changes,
    find_meal,
    generate_diet_plan,
    generate_workout_plan,
    remove_meal,
)

router = APIRouter(prefix="/coach", tags=["coach"])

REVIEWS_SHOWN = 12

_CUSTOMER_LOADS = (
    joinedload(Customer.user),
    selectinload(Customer.plans),
    selectinload(Customer.requests),
)


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
        country=customer.country,
        height_cm=customer.height_cm,
        weight_kg=customer.weight_kg,
        waist_cm=customer.waist_cm,
        neck_cm=customer.neck_cm,
        hip_cm=customer.hip_cm,
        activity_level=customer.activity_level,
        primary_goal=customer.primary_goal,
        diet_type=customer.diet_type,
        budget_level=customer.budget_level,
        dietary_preferences=customer.dietary_preferences,
        medical_conditions=customer.medical_conditions,
        stress_level=customer.stress_level,
        injuries=customer.injuries,
        training_experience=customer.training_experience,
        training_location=customer.training_location,
        training_days_per_week=customer.training_days_per_week,
        profile_updated_at=customer.profile_updated_at,
        calorie_adjustment=customer.calorie_adjustment or 0,
        bmi=bmi,
        workout_plan_count=sum(1 for p in customer.plans if p.plan_type == "workout"),
        diet_plan_count=sum(1 for p in customer.plans if p.plan_type == "diet"),
        pending_requests=sum(1 for r in customer.requests if r.status == "pending"),
    )


async def _load_customer(db: AsyncSession, customer_id: uuid.UUID) -> Customer:
    result = await db.execute(
        select(Customer)
        .where(Customer.id == customer_id)
        .options(*_CUSTOMER_LOADS)
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
        .options(*_CUSTOMER_LOADS)
        .order_by(Customer.id)
    )
    return [_summary(c) for c in result.scalars().all()]


@router.post("/customers/link", response_model=CustomerSummary)
@limiter.limit(LOGIN_LIMIT)
async def link_customer(
    request: Request,
    payload: LinkCustomerRequest,
    coach: Coach = Depends(get_current_coach),
    db: AsyncSession = Depends(get_db),
) -> CustomerSummary:
    """Adds a customer using the share code they gave the coach. This is the consent step."""
    result = await db.execute(
        select(Customer)
        .where(Customer.share_code == payload.share_code.strip().upper())
        .options(*_CUSTOMER_LOADS)
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No customer found with that share code")
    if customer.coach_id == coach.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "This customer is already on your roster")
    if customer.coach_id is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This customer already has a coach")

    customer.coach_id = coach.id
    # Single use: a code seen once can't be used to re-add the customer after they're removed.
    customer.share_code = generate_share_code()
    await db.commit()
    return _summary(await _load_customer(db, customer.id))


@router.post("/customers/{customer_id}/remove", response_model=MessageResponse)
async def remove_customer(
    customer_id: uuid.UUID,
    user: User = Depends(get_current_user),
    coach: Coach = Depends(get_current_coach),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Ends coaching. The customer keeps their plans and can share their code with a new coach."""
    customer = await _load_my_customer(db, coach, customer_id)
    await end_coaching(db, customer, coach.id, "Closed because your coach ended coaching.")

    db.add(
        Notification(
            user_id=customer.user_id,
            message=f"{user.full_name} removed you from their roster. "
            "Share your code with a coach to get a new one.",
        )
    )
    await db.commit()
    return MessageResponse(message=f"{customer.user.full_name} was removed from your roster.")


@router.get("/customers/{customer_id}", response_model=CustomerDetail)
async def get_customer(
    customer_id: uuid.UUID,
    coach: Coach = Depends(get_current_coach),
    db: AsyncSession = Depends(get_db),
) -> CustomerDetail:
    customer = await _load_my_customer(db, coach, customer_id)
    if await ensure_weekly_review(db, customer, customer.user.full_name):
        await db.commit()

    reviews = await db.scalars(
        select(WeeklyReview)
        .where(WeeklyReview.customer_id == customer.id)
        .order_by(WeeklyReview.period_end.desc())
        .limit(REVIEWS_SHOWN)
    )
    return CustomerDetail(
        **_summary(customer).model_dump(),
        metrics=metrics_for(customer),
        plans=sorted(customer.plans, key=lambda p: p.created_at, reverse=True),
        reviews=[WeeklyReviewResponse.model_validate(r) for r in reviews.all()],
    )


async def _my_open_review(db: AsyncSession, coach: Coach, review_id: uuid.UUID) -> tuple:
    review = await db.get(WeeklyReview, review_id)
    if review is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Review not found")
    customer = await _load_my_customer(db, coach, review.customer_id)
    if review.status != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, "This review has no pending adjustment")
    if review.stats.get("goal") != customer.primary_goal:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The customer changed goal after this review, so its suggestion no longer applies",
        )
    return review, customer


@router.post("/reviews/{review_id}/apply", response_model=WeeklyReviewResponse)
async def apply_weekly_review(
    review_id: uuid.UUID,
    coach: Coach = Depends(get_current_coach),
    db: AsyncSession = Depends(get_db),
) -> WeeklyReview:
    """FR-5.7: adds the review's recommendation to the customer's calorie target."""
    review, customer = await _my_open_review(db, coach, review_id)
    total = apply_review(review, customer)
    change = review.recommended_adjustment
    db.add(
        Notification(
            user_id=customer.user_id,
            message=f"Your coach {'raised' if change > 0 else 'lowered'} your daily calories by "
            f"{abs(change)} kcal after your weekly review ({total:+d} kcal in total). "
            "Your diet plan will be updated.",
        )
    )
    await db.commit()
    await db.refresh(review)
    return review


@router.post("/reviews/{review_id}/dismiss", response_model=WeeklyReviewResponse)
async def dismiss_weekly_review(
    review_id: uuid.UUID,
    coach: Coach = Depends(get_current_coach),
    db: AsyncSession = Depends(get_db),
) -> WeeklyReview:
    review, _ = await _my_open_review(db, coach, review_id)
    review.status = "dismissed"
    review.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(review)
    return review


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


async def _my_diet_plan(db: AsyncSession, coach: Coach, plan_id: uuid.UUID) -> WorkoutDietPlan:
    plan = await db.get(WorkoutDietPlan, plan_id)
    if plan is None or plan.coach_id != coach.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan not found")
    customer = await db.get(Customer, plan.customer_id)
    if customer is None or customer.coach_id != coach.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This customer is not assigned to you")
    if plan.plan_type != "diet":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only diet plans have meals")
    return plan


@router.put("/plans/{plan_id}/meals", response_model=PlanResponse)
async def update_meal(
    plan_id: uuid.UUID,
    payload: MealUpdate,
    coach: Coach = Depends(get_current_coach),
    db: AsyncSession = Depends(get_db),
) -> WorkoutDietPlan:
    plan = await _my_diet_plan(db, coach, plan_id)
    if find_meal(plan.content, payload.day, payload.session) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Meal not found")
    plan.content = apply_meal_changes(
        plan.content, [payload.model_dump()], option="Updated by coach"
    )
    await db.commit()
    await db.refresh(plan)
    return plan


@router.delete("/plans/{plan_id}/meals", response_model=PlanResponse)
async def delete_meal(
    plan_id: uuid.UUID,
    day: str = Query(min_length=1, max_length=20),
    session: str = Query(min_length=1, max_length=40),
    coach: Coach = Depends(get_current_coach),
    db: AsyncSession = Depends(get_db),
) -> WorkoutDietPlan:
    plan = await _my_diet_plan(db, coach, plan_id)
    if find_meal(plan.content, day, session) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Meal not found")
    plan.content = remove_meal(plan.content, day, session)
    await db.commit()
    await db.refresh(plan)
    return plan
