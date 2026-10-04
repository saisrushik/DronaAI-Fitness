"""Requests customers raise with their coach, and the coach's responses to them."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_current_coach, get_current_customer, get_current_user
from app.db.models import Coach, Customer, CustomerRequest, Notification, User, WorkoutDietPlan
from app.db.session import get_db
from app.schemas.user import (
    CoachResponse,
    CustomerRequestCreate,
    CustomerRequestResponse,
    DietChangeApproval,
    MealRequestCreate,
)
from app.services.plan_generator import apply_meal_changes, find_meal, meal_diff

router = APIRouter(prefix="/requests", tags=["requests"])

LABELS = {
    "meal": "meal request",
    "workout": "workout change request",
    "injury": "injury report",
    "query": "question",
}
CREATED = {
    "meal": "sent a meal request",
    "workout": "requested a workout change",
    "injury": "reported an injury",
    "query": "asked a question",
}
RESOLVED = {"approved": "approved", "rejected": "declined", "resolved": "responded to"}

_LOADS = (
    joinedload(CustomerRequest.customer).joinedload(Customer.user),
    joinedload(CustomerRequest.plan),
)


def _requested_meals(request: CustomerRequest) -> list[dict] | None:
    """While pending, diffs each meal against the current plan so the coach sees only changes."""
    if request.requested_meals is None or request.status != "pending" or request.plan is None:
        return request.requested_meals
    meals = []
    for meal in request.requested_meals:
        session = find_meal(request.plan.content, meal["day"], meal["session"])
        if session is None:
            meals.append({**meal, "kept": [], "added": meal["items"], "removed": []})
            continue
        kept, added, removed = meal_diff(session["items"], meal["items"])
        meals.append({**meal, "kept": [i["name"] for i in kept], "added": added, "removed": removed})
    return meals


def _response(request: CustomerRequest) -> CustomerRequestResponse:
    return CustomerRequestResponse(
        id=request.id,
        customer_id=request.customer_id,
        customer_name=request.customer.user.full_name,
        plan_id=request.plan_id,
        plan_title=request.plan.title if request.plan else None,
        request_type=request.request_type,
        status=request.status,
        description=request.description,
        requested_meals=_requested_meals(request),
        approved_meals=request.approved_meals,
        coach_note=request.coach_note,
        created_at=request.created_at,
        resolved_at=request.resolved_at,
    )


async def _load(db: AsyncSession, request_id: uuid.UUID) -> CustomerRequest | None:
    return await db.scalar(
        select(CustomerRequest)
        .where(CustomerRequest.id == request_id)
        .options(*_LOADS)
        .execution_options(populate_existing=True)
    )


@router.get("", response_model=list[CustomerRequestResponse])
async def list_requests(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[CustomerRequestResponse]:
    query = select(CustomerRequest).options(*_LOADS).order_by(CustomerRequest.created_at.desc())
    if user.coach is not None:
        query = query.where(CustomerRequest.coach_id == user.coach.id)
    elif user.customer is not None:
        query = query.where(CustomerRequest.customer_id == user.customer.id)
    else:
        return []
    result = await db.execute(query)
    return [_response(request) for request in result.scalars().all()]


async def _submit(
    db: AsyncSession, user: User, customer: Customer, request: CustomerRequest
) -> CustomerRequestResponse:
    """Saves the request and notifies both the coach and the customer."""
    db.add(request)
    await db.flush()

    coach_user_id = await db.scalar(select(Coach.user_id).where(Coach.id == customer.coach_id))
    db.add_all(
        [
            Notification(
                user_id=coach_user_id,
                request_id=request.id,
                message=f"{user.full_name} {CREATED[request.request_type]}",
            ),
            Notification(
                user_id=user.id,
                request_id=request.id,
                message=f"Your {LABELS[request.request_type]} was sent to your coach",
            ),
        ]
    )
    await db.commit()
    return _response(await _load(db, request.id))


def _require_coach(customer: Customer) -> uuid.UUID:
    if customer.coach_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "You need a coach before you can send requests"
        )
    return customer.coach_id


@router.post("", response_model=CustomerRequestResponse, status_code=201)
async def create_request(
    payload: CustomerRequestCreate,
    user: User = Depends(get_current_user),
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> CustomerRequestResponse:
    request = CustomerRequest(
        customer_id=customer.id,
        coach_id=_require_coach(customer),
        request_type=payload.request_type,
        status="pending",
        description=payload.description,
        coach_note="",
    )
    return await _submit(db, user, customer, request)


@router.post("/meal", response_model=CustomerRequestResponse, status_code=201)
async def create_meal_request(
    payload: MealRequestCreate,
    user: User = Depends(get_current_user),
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> CustomerRequestResponse:
    """Customers name foods only; the coach sets portions and nutrition when approving."""
    plan = await db.get(WorkoutDietPlan, payload.plan_id)
    if plan is None or plan.customer_id != customer.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan not found")
    if plan.plan_type != "diet":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only diet plans can be edited")
    if plan.approved_at is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Accept the plan before editing it")
    coach_id = _require_coach(customer)

    meals = []
    for meal in payload.meals:
        session = find_meal(plan.content, meal.day, meal.session)
        if session is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"{meal.day} {meal.session} is not in this plan"
            )
        _, added, removed = meal_diff(session["items"], meal.items)
        if added or removed:
            meals.append({**meal.model_dump(), "added": added, "removed": removed})
    if not meals:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "None of these meals were changed")

    pending = await db.scalar(
        select(CustomerRequest.id).where(
            CustomerRequest.plan_id == plan.id, CustomerRequest.status == "pending"
        )
    )
    if pending is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "You already have a meal request waiting for your coach"
        )

    request = CustomerRequest(
        customer_id=customer.id,
        coach_id=coach_id,
        plan_id=plan.id,
        request_type="meal",
        status="pending",
        requested_meals=meals,
        description=payload.description.strip(),
        coach_note="",
    )
    return await _submit(db, user, customer, request)


async def _pending_for(db: AsyncSession, coach: Coach, request_id: uuid.UUID) -> CustomerRequest:
    request = await _load(db, request_id)
    # The customer may have moved to another coach since asking.
    if request is None or request.coach_id != coach.id or request.customer.coach_id != coach.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    if request.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "This request was already reviewed")
    return request


async def _close(
    db: AsyncSession, request: CustomerRequest, coach_user: User, new_status: str, note: str
) -> CustomerRequestResponse:
    request.status = new_status
    request.coach_note = note.strip()
    request.resolved_at = datetime.now(timezone.utc)
    db.add(
        Notification(
            user_id=request.customer.user_id,
            request_id=request.id,
            message=f"{coach_user.full_name} {RESOLVED[new_status]} your "
            f"{LABELS[request.request_type]}",
        )
    )
    await db.commit()
    return _response(await _load(db, request.id))


@router.post("/{request_id}/approve-meal", response_model=CustomerRequestResponse)
async def approve_meal_request(
    request_id: uuid.UUID,
    payload: DietChangeApproval,
    user: User = Depends(get_current_user),
    coach: Coach = Depends(get_current_coach),
    db: AsyncSession = Depends(get_db),
) -> CustomerRequestResponse:
    request = await _pending_for(db, coach, request_id)
    if request.request_type != "meal" or request.plan is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This is not a meal request")

    requested = {(m["day"], m["session"]): m for m in request.requested_meals or []}
    if set(requested) != {(m.day, m.session) for m in payload.meals}:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Provide nutrition for exactly the requested meals"
        )

    # Foods the customer kept stay as they are; the coach only sets values for new foods.
    final_meals = []
    for meal in payload.meals:
        session = find_meal(request.plan.content, meal.day, meal.session)
        if session is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"{meal.day} {meal.session} is no longer in this plan; decline the request",
            )
        kept, _, _ = meal_diff(session["items"], requested[(meal.day, meal.session)]["items"])
        items = kept + [item.model_dump() for item in meal.items]
        if not items:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"{meal.day} {meal.session} needs at least one food"
            )
        final_meals.append({"day": meal.day, "session": meal.session, "items": items})

    request.plan.content = apply_meal_changes(request.plan.content, final_meals)
    request.approved_meals = [meal.model_dump() for meal in payload.meals]
    return await _close(db, request, user, "approved", payload.note)


@router.post("/{request_id}/resolve", response_model=CustomerRequestResponse)
async def resolve_request(
    request_id: uuid.UUID,
    payload: CoachResponse,
    user: User = Depends(get_current_user),
    coach: Coach = Depends(get_current_coach),
    db: AsyncSession = Depends(get_db),
) -> CustomerRequestResponse:
    request = await _pending_for(db, coach, request_id)
    if request.request_type == "meal":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Meal requests need nutrition values to be approved"
        )
    if not payload.note.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Add a response for your customer")
    return await _close(db, request, user, "resolved", payload.note)


@router.post("/{request_id}/reject", response_model=CustomerRequestResponse)
async def reject_request(
    request_id: uuid.UUID,
    payload: CoachResponse,
    user: User = Depends(get_current_user),
    coach: Coach = Depends(get_current_coach),
    db: AsyncSession = Depends(get_db),
) -> CustomerRequestResponse:
    request = await _pending_for(db, coach, request_id)
    if request.request_type in ("query", "injury"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Queries and injury reports need a response, not a decline"
        )
    return await _close(db, request, user, "rejected", payload.note)
