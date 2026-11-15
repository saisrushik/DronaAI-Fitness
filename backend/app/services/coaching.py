"""Ending the link between a coach and a customer, whoever initiates it."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Coach, Customer, CustomerRequest, Notification


async def end_coaching(
    db: AsyncSession, customer: Customer, coach_id: uuid.UUID, note: str
) -> None:
    """Unlinks the customer and closes requests still waiting on that coach.

    The customer keeps their plans and history, and can share their code with a new coach.
    """
    customer.coach_id = None
    pending = await db.scalars(
        select(CustomerRequest).where(
            CustomerRequest.customer_id == customer.id,
            CustomerRequest.coach_id == coach_id,
            CustomerRequest.status == "pending",
        )
    )
    now = datetime.now(timezone.utc)
    for request in pending:
        request.status = "rejected"
        request.coach_note = note
        request.resolved_at = now


async def record_profile_change(
    db: AsyncSession, customer: Customer, customer_name: str, *, first_time: bool
) -> None:
    """FR-1.8: lets the coach know the customer's plans may need regenerating."""
    if not first_time:
        customer.profile_updated_at = datetime.now(timezone.utc)
    if customer.coach_id is None:
        return

    coach_user_id = await db.scalar(select(Coach.user_id).where(Coach.id == customer.coach_id))
    message = (
        f"{customer_name} completed their profile. You can now build their plans."
        if first_time
        else f"{customer_name} updated their profile. Review their plans and regenerate "
        "them if needed."
    )
    db.add(Notification(user_id=coach_user_id, message=message))
