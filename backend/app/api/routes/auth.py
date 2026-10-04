from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

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
    AccountUpdate,
    CoachProfileUpdate,
    CustomerProfileUpdate,
    LoginRequest,
    MeResponse,
    MessageResponse,
    RegisterRequest,
)
from app.services.measurements import body_values, changed_values, measurement_from
from app.services.metrics import metrics_for

router = APIRouter(prefix="/auth", tags=["auth"])

# Checked against when the email is unknown, so response time doesn't reveal which emails exist.
_DUMMY_HASH = hash_password("timing-equaliser")


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
    # Older rows may have been stored with mixed case.
    result = await db.execute(select(User).where(func.lower(User.email) == email.lower()))
    return result.scalars().first()


async def _reload(db: AsyncSession, user_id) -> User:
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(joinedload(User.coach), joinedload(User.customer))
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
        customer = Customer(
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
        db.add(customer)
        await db.flush()
        # Sign-up measurements are the first point in the customer's history.
        first = measurement_from(customer, body_values(customer))
        if first is not None:
            db.add(first)
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
    if user is None:
        verify_password(payload.password, _DUMMY_HASH)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    if not verify_password(payload.password, user.password_hash):
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

    customer = current_user.customer
    before = body_values(customer)
    for field, value in payload.model_dump().items():
        setattr(customer, field, value)
    customer.profile_completed = True

    # Edits to measurements on the profile form also count as a new log entry.
    entry = measurement_from(customer, changed_values(before, body_values(customer)))
    if entry is not None:
        db.add(entry)

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


@router.put("/me/account", response_model=MeResponse)
@limiter.limit(LOGIN_LIMIT)
async def update_account(
    request: Request,
    payload: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    user = current_user
    email_changed = payload.email.lower() != user.email.lower()
    role_changed = payload.role != user.role

    if email_changed or role_changed:
        if not payload.current_password or not verify_password(
            payload.current_password, user.password_hash
        ):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Enter your current password to change your email or role",
            )
    if email_changed and await _by_email(db, payload.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email is already registered")

    if role_changed and payload.role == "coach":
        if user.customer and user.customer.coach_id:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Ask your coach to remove you before switching to a coach account",
            )
        if user.coach is None:
            db.add(
                Coach(
                    user_id=user.id,
                    gender=payload.gender,
                    date_of_birth=payload.date_of_birth,
                )
            )
    elif role_changed and payload.role == "customer":
        if user.coach and await db.scalar(
            select(func.count()).select_from(Customer).where(Customer.coach_id == user.coach.id)
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Remove your customers before switching to a customer account",
            )
        if user.customer is None:
            if payload.gender is None or payload.date_of_birth is None:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Customers need a gender and date of birth for their health metrics",
                )
            db.add(
                Customer(
                    user_id=user.id,
                    share_code=generate_share_code(),
                    gender=payload.gender,
                    date_of_birth=payload.date_of_birth,
                )
            )

    user.first_name = payload.first_name
    user.last_name = payload.last_name
    user.email = payload.email
    user.role = payload.role

    # Demographics live on the profile for the account's (new) role.
    profile = user.coach if payload.role == "coach" else user.customer
    if profile is not None:
        if payload.gender is not None:
            profile.gender = payload.gender
        if payload.date_of_birth is not None:
            profile.date_of_birth = payload.date_of_birth

    user_id = user.id
    await db.commit()
    # A role switch may have created a profile row the loaded user doesn't know about yet.
    db.expire_all()
    return _to_me(await _reload(db, user_id))
