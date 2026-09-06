import uuid

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import decode_token
from app.db.models import Coach, Customer, User
from app.db.session import get_db

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    # The browser uses an httpOnly cookie; the bearer header is kept for API clients.
    token = request.cookies.get(settings.COOKIE_NAME) or (
        credentials.credentials if credentials else None
    )
    if token is None:
        raise invalid

    subject = decode_token(token)
    if subject is None:
        raise invalid

    try:
        user_id = uuid.UUID(subject)
    except ValueError:
        raise invalid from None

    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.coach), selectinload(User.customer))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise invalid
    return user


async def get_current_coach(current_user: User = Depends(get_current_user)) -> Coach:
    if current_user.role != "coach" or current_user.coach is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Coach account required")
    return current_user.coach


async def get_current_customer(current_user: User = Depends(get_current_user)) -> Customer:
    if current_user.role != "customer" or current_user.customer is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Customer account required")
    return current_user.customer
