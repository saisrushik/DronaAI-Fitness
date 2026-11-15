"""Server-side sessions behind the access and refresh cookies.

The access token is short-lived and names its session; every request checks that session is
still active, so logging out or revoking takes effect immediately. The refresh token is rotated
on each use, and replaying an already-used one revokes the whole session.
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Request, Response
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import ACCESS, REFRESH, create_token, decode_token, new_token_id
from app.db.models import AuthSession

# How long the previous refresh token keeps working after a rotation (parallel tabs).
REUSE_GRACE = timedelta(seconds=60)
REFRESH_COOKIE_PATH = f"{settings.API_V1_PREFIX}/auth"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _utc(value: datetime) -> datetime:
    # SQLite hands timezone-aware columns back without tzinfo.
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _refresh_lifetime() -> timedelta:
    return timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


def is_active(session: AuthSession) -> bool:
    return session.revoked_at is None and _utc(session.expires_at) > _now()


async def start_session(db: AsyncSession, user_id: uuid.UUID) -> AuthSession:
    session = AuthSession(
        user_id=user_id,
        refresh_jti=new_token_id(),
        expires_at=_now() + _refresh_lifetime(),
    )
    db.add(session)
    await db.flush()
    return session


def rotate(session: AuthSession) -> None:
    session.previous_jti = session.refresh_jti
    session.refresh_jti = new_token_id()
    session.rotated_at = _now()
    session.expires_at = _now() + _refresh_lifetime()


def is_recent_previous(session: AuthSession, jti: str) -> bool:
    return (
        session.previous_jti == jti
        and session.rotated_at is not None
        and _now() - _utc(session.rotated_at) < REUSE_GRACE
    )


def revoke(session: AuthSession) -> None:
    if session.revoked_at is None:
        session.revoked_at = _now()


async def revoke_all(
    db: AsyncSession, user_id: uuid.UUID, keep: uuid.UUID | None = None
) -> None:
    """Signs the user out everywhere, optionally except the session making the request."""
    query = update(AuthSession).where(
        AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None)
    )
    if keep is not None:
        query = query.where(AuthSession.id != keep)
    await db.execute(query.values(revoked_at=_now()))


def session_id_from_request(request: Request, bearer: str | None = None) -> uuid.UUID | None:
    """The session this browser is using, read from whichever token it still holds."""
    candidates = [
        (request.cookies.get(settings.REFRESH_COOKIE_NAME), REFRESH),
        (request.cookies.get(settings.COOKIE_NAME), ACCESS),
        (bearer, ACCESS),
    ]
    for token, purpose in candidates:
        payload = decode_token(token, purpose) if token else None
        if payload and payload.get("sid"):
            try:
                return uuid.UUID(payload["sid"])
            except ValueError:
                return None
    return None


def set_auth_cookies(response: Response, session: AuthSession) -> None:
    user_id = str(session.user_id)
    common = {
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
    }
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=create_token(user_id, ACCESS, sid=str(session.id)),
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
        **common,
    )
    # Scoped to the auth routes so it isn't sent with every API call.
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=create_token(
            user_id,
            REFRESH,
            expires_in=_refresh_lifetime(),
            sid=str(session.id),
            jti=session.refresh_jti,
        ),
        max_age=int(_refresh_lifetime().total_seconds()),
        path=REFRESH_COOKIE_PATH,
        **common,
    )


def clear_auth_cookies(response: Response) -> None:
    common = {
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
    }
    response.delete_cookie(key=settings.COOKIE_NAME, path="/", **common)
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH, **common
    )
