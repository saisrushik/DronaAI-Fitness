import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import Notification, User
from app.db.session import get_db
from app.schemas.user import MessageResponse, NotificationList, NotificationResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])

PAGE_SIZE = 30


@router.get("", response_model=NotificationList)
async def list_notifications(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> NotificationList:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(PAGE_SIZE)
    )
    unread = await db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
    )
    return NotificationList(
        unread=unread or 0,
        items=[NotificationResponse.model_validate(n) for n in result.scalars().all()],
    )


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Notification:
    notification = await db.get(Notification, notification_id)
    if notification is None or notification.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc)
        await db.commit()
    return notification


@router.post("/read-all", response_model=MessageResponse)
async def mark_all_read(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return MessageResponse(message="All notifications marked as read")
