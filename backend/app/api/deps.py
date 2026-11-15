import uuid

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.core.security import decode_token
from app.db.models import AuthSession, Coach, Customer, User
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

    payload = decode_token(token)
    if payload is None:
        raise invalid

    try:
        user_id = uuid.UUID(payload["sub"])
        session_id = uuid.UUID(payload.get("sid", ""))
    except (TypeError, ValueError):
        raise invalid from None

    # The session must still be live, so logout and revocation take effect immediately.
    result = await db.execute(
        select(User)
        .join(AuthSession, AuthSession.user_id == User.id)
        .where(
            User.id == user_id,
            AuthSession.id == session_id,
            AuthSession.revoked_at.is_(None),
        )
        .options(joinedload(User.coach), joinedload(User.customer))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise invalid
    request.state.session_id = session_id
    return user


async def get_current_coach(current_user: User = Depends(get_current_user)) -> Coach:
    if current_user.role != "coach" or current_user.coach is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Coach account required")
    return current_user.coach


async def get_current_customer(current_user: User = Depends(get_current_user)) -> Customer:
    if current_user.role != "customer" or current_user.customer is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Customer account required")
    return current_user.customer
