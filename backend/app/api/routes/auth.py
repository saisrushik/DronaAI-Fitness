import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import bearer_scheme, get_current_user
from app.core.config import settings
from app.core.rate_limit import (
    EXPORT_LIMIT,
    LOGIN_LIMIT,
    REFRESH_LIMIT,
    REGISTER_LIMIT,
    limiter,
)
from app.core.security import (
    REFRESH,
    decode_token,
    generate_share_code,
    hash_password,
    verify_password,
)
from app.db.models import AuthSession, Coach, Customer, Notification, User
from app.db.session import get_db
from app.schemas.user import (
    AccountDelete,
    AccountUpdate,
    CoachProfileUpdate,
    CustomerProfileUpdate,
    LoginRequest,
    MeResponse,
    MessageResponse,
    PreferencesUpdate,
    RegisterRequest,
)
from app.services.auth_sessions import (
    clear_auth_cookies,
    is_active,
    is_recent_previous,
    revoke,
    revoke_all,
    rotate,
    session_id_from_request,
    set_auth_cookies,
    start_session,
)
from app.services.coaching import end_coaching, record_profile_change
from app.services.data_export import build_export
from app.services.measurements import body_values, changed_values, measurement_from
from app.services.metrics import metrics_for
from app.services.weekly_review import supersede_open_reviews

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
        unit_system=user.unit_system or "metric",
        profile_completed=bool(profile and profile.profile_completed),
        coach=user.coach,
        customer=user.customer,
        metrics=metrics_for(user.customer),
    )


async def _sign_in(request: Request, response: Response, db: AsyncSession, user_id) -> None:
    """Starts a new session, ending whichever one this browser held before."""
    await _end_browser_session(request, db)
    session = await start_session(db, user_id)
    await db.commit()
    set_auth_cookies(response, session)


async def _end_browser_session(
    request: Request, db: AsyncSession, bearer: str | None = None
) -> None:
    session_id = session_id_from_request(request, bearer)
    if session_id is None:
        return
    session = await db.get(AuthSession, session_id)
    if session is not None:
        revoke(session)


def _session_expired() -> JSONResponse:
    # Returned rather than raised so the cookie-clearing headers reach the browser.
    response = JSONResponse(
        {"detail": "Your session has expired. Please log in again."},
        status_code=status.HTTP_401_UNAUTHORIZED,
    )
    clear_auth_cookies(response)
    return response


async def _by_email(db: AsyncSession, email: str) -> User | None:
    # Older rows may have been stored with mixed case.
    result = await db.execute(select(User).where(func.lower(User.email) == email.lower()))
    return result.scalars().first()


def _blank(value):  # type: ignore[no-untyped-def]
    """Treats missing and empty values alike when deciding whether a profile changed."""
    return None if value is None or value == [] or value == "" else value


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
            country=payload.country,
            height_cm=payload.height_cm,
            weight_kg=payload.weight_kg,
            waist_cm=payload.waist_cm,
            neck_cm=payload.neck_cm,
            hip_cm=payload.hip_cm,
        )
        db.add(customer)
        await db.flush()
        # Any sign-up measurements are the first point in the customer's history.
        first = measurement_from(customer, body_values(customer))
        if first is not None:
            db.add(first)

    await _sign_in(request, response, db, user.id)
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

    await _sign_in(request, response, db, user.id)
    return _to_me(await _reload(db, user.id))


@router.post("/refresh", response_model=MessageResponse)
@limiter.limit(REFRESH_LIMIT)
async def refresh_session(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    """Swaps a refresh token for a new access token, rotating the refresh token as it goes."""
    token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    payload = decode_token(token, REFRESH) if token else None
    if payload is None:
        return _session_expired()
    try:
        session_id = uuid.UUID(payload.get("sid", ""))
    except (TypeError, ValueError):
        return _session_expired()

    # Locked so two tabs refreshing at the same instant are serialised: the second then sees the
    # first one's rotation and takes the grace path instead of overwriting it.
    session = await db.get(AuthSession, session_id, with_for_update=True)
    if session is None or str(session.user_id) != payload["sub"] or not is_active(session):
        return _session_expired()

    jti = payload.get("jti")
    if jti == session.refresh_jti:
        rotate(session)
    elif not is_recent_previous(session, jti):
        # An already-used refresh token came back: treat it as stolen and end the session.
        revoke(session)
        await db.commit()
        return _session_expired()

    await db.commit()
    set_auth_cookies(response, session)
    return MessageResponse(message="Session refreshed.")


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await _end_browser_session(request, db, credentials.credentials if credentials else None)
    await db.commit()
    clear_auth_cookies(response)
    return MessageResponse(message="Logged out.")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_everywhere(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await revoke_all(db, current_user.id)
    await db.commit()
    clear_auth_cookies(response)
    return MessageResponse(message="Logged out on all devices.")


@router.get("/me", response_model=MeResponse)
async def read_me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return _to_me(current_user)


@router.put("/me/preferences", response_model=MeResponse)
async def update_preferences(
    payload: PreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    """Display settings that don't affect any calculation, such as metric or imperial units."""
    current_user.unit_system = payload.unit_system
    await db.commit()
    return _to_me(await _reload(db, current_user.id))


@router.put("/me/customer-profile", response_model=MeResponse)
async def update_customer_profile(
    payload: CustomerProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    if current_user.customer is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Customer account required")

    customer = current_user.customer
    first_time = not customer.profile_completed
    values = payload.model_dump(mode="json")
    before_profile = {field: getattr(customer, field) for field in values}
    before = body_values(customer)
    for field, value in values.items():
        setattr(customer, field, value)
    customer.profile_completed = True
    # Review adjustments were tuned for the old goal's expected rate, so they no longer apply.
    if not first_time and before_profile["primary_goal"] != customer.primary_goal:
        customer.calorie_adjustment = 0
        await supersede_open_reviews(db, customer)

    # Edits to measurements on the profile form also count as a new log entry.
    entry = measurement_from(customer, changed_values(before, body_values(customer)))
    if entry is not None:
        db.add(entry)

    if first_time or any(
        _blank(before_profile[field]) != _blank(value) for field, value in values.items()
    ):
        await record_profile_change(
            db, customer, current_user.full_name, first_time=first_time
        )

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
                    country=payload.country or "IN",
                )
            )

    user.first_name = payload.first_name
    user.last_name = payload.last_name
    user.email = payload.email
    user.role = payload.role

    # Demographics live on the profile for the account's (new) role.
    profile = user.coach if payload.role == "coach" else user.customer
    demographics_before = (
        (profile.gender, profile.date_of_birth, getattr(profile, "country", None))
        if profile is not None
        else None
    )
    if profile is not None:
        if payload.gender is not None:
            profile.gender = payload.gender
        if payload.date_of_birth is not None:
            profile.date_of_birth = payload.date_of_birth
    if payload.role == "customer" and user.customer is not None and payload.country:
        user.customer.country = payload.country

    # Age, gender and country feed the calculators, so the coach may need new plans.
    customer = user.customer if payload.role == "customer" else None
    if (
        customer is not None
        and customer.profile_completed
        and demographics_before is not None
        and demographics_before != (customer.gender, customer.date_of_birth, customer.country)
    ):
        await record_profile_change(db, customer, user.full_name, first_time=False)

    # Other devices signed in under the old email or role must sign in again.
    if email_changed or role_changed:
        await revoke_all(db, user.id, keep=request.state.session_id)

    user_id = user.id
    await db.commit()
    # A role switch may have created a profile row the loaded user doesn't know about yet.
    db.expire_all()
    return _to_me(await _reload(db, user_id))


@router.get("/me/export")
@limiter.limit(EXPORT_LIMIT)
async def export_my_data(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Everything stored about the signed-in user, as a downloadable JSON file."""
    data = await build_export(db, current_user)
    return JSONResponse(
        jsonable_encoder(data),
        headers={
            "Content-Disposition": 'attachment; filename="dronaai-fit-my-data.json"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/me/delete", response_model=MessageResponse)
@limiter.limit(LOGIN_LIMIT)
async def delete_account(
    request: Request,
    payload: AccountDelete,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Permanently deletes the account and everything that belongs to it."""
    if not verify_password(payload.password, current_user.password_hash):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Incorrect password")

    if current_user.coach is not None:
        # Customers keep their plans and history; they just lose access to this coach.
        customers = await db.scalars(
            select(Customer).where(Customer.coach_id == current_user.coach.id)
        )
        for customer in customers.all():
            await end_coaching(
                db,
                customer,
                current_user.coach.id,
                "Closed because your coach deleted their account.",
            )
            db.add(
                Notification(
                    user_id=customer.user_id,
                    message=f"{current_user.full_name} closed their account. "
                    "Share your code with a new coach to continue.",
                )
            )
        await db.flush()

    # Foreign keys cascade from users to the profile, plans, logs, measurements, requests,
    # notifications and sessions. Plans a coach wrote for others keep existing without them.
    await db.execute(delete(User).where(User.id == current_user.id))
    await db.commit()

    clear_auth_cookies(response)
    return MessageResponse(message="Your account and all of its data have been deleted.")
