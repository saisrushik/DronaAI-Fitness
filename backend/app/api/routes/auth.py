from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.rate_limit import LOGIN_LIMIT, REGISTER_LIMIT, limiter
from app.core.security import (
    create_token,
    generate_share_code,
    hash_password,
    verify_password,
)
from app.db.models import Coach, Customer, User
from app.db.session import get_db
from app.schemas.user import (
    CoachProfileUpdate,
    CustomerProfileUpdate,
    LoginRequest,
    MeResponse,
    MessageResponse,
    RegisterRequest,
)
from app.services.metrics import metrics_for

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_me(user: User) -> MeResponse:
    profile = user.coach if user.role == "coach" else user.customer
    return MeResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        role=user.role,
        profile_completed=bool(profile and profile.profile_completed),
        coach=user.coach,
        customer=user.customer,
        metrics=metrics_for(user.customer),
    )


def _set_session_cookie(response: Response, user_id: str) -> None:
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=create_token(user_id),
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


async def _by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def _reload(db: AsyncSession, user_id) -> User:
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.coach), selectinload(User.customer))
    )
    return result.scalar_one()


@router.post("/register", response_model=MeResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(REGISTER_LIMIT)
async def register(
    request: Request,
    payload: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    if await _by_email(db, payload.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email is already registered")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=payload.role,
        disclaimer_accepted_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()

    if payload.role == "coach":
        db.add(Coach(user_id=user.id))
    else:
        db.add(
            Customer(
                user_id=user.id,
                share_code=generate_share_code(),
                date_of_birth=payload.date_of_birth,
                gender=payload.gender,
                height_cm=payload.height_cm,
                weight_kg=payload.weight_kg,
                waist_cm=payload.waist_cm,
                neck_cm=payload.neck_cm,
                hip_cm=payload.hip_cm,
            )
        )
    await db.commit()

    _set_session_cookie(response, str(user.id))
    return _to_me(await _reload(db, user.id))


@router.post("/login", response_model=MeResponse)
@limiter.limit(LOGIN_LIMIT)
async def login(
    request: Request,
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    user = await _by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")

    _set_session_cookie(response, str(user.id))
    return _to_me(await _reload(db, user.id))


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response) -> MessageResponse:
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )
    return MessageResponse(message="Logged out.")


@router.get("/me", response_model=MeResponse)
async def read_me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return _to_me(current_user)


@router.put("/me/customer-profile", response_model=MeResponse)
async def update_customer_profile(
    payload: CustomerProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    if current_user.customer is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Customer account required")

    for field, value in payload.model_dump().items():
        setattr(current_user.customer, field, value)
    current_user.customer.profile_completed = True

    await db.commit()
    return _to_me(await _reload(db, current_user.id))


@router.put("/me/coach-profile", response_model=MeResponse)
async def update_coach_profile(
    payload: CoachProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    if current_user.coach is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Coach account required")

    for field, value in payload.model_dump().items():
        setattr(current_user.coach, field, value)
    current_user.coach.profile_completed = True

    await db.commit()
    return _to_me(await _reload(db, current_user.id))
