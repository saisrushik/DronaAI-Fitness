from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_customer
from app.db.models import BodyMeasurement, Customer
from app.db.session import get_db
from app.schemas.user import MeasurementCreate, MeasurementResponse
from app.services.measurements import measurement_from

router = APIRouter(prefix="/measurements", tags=["measurements"])


def _as_utc(moment: datetime) -> datetime:
    # SQLite returns naive datetimes in tests; Postgres returns aware ones.
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


@router.get("", response_model=list[MeasurementResponse])
async def my_measurements(
    customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_db)
) -> list[BodyMeasurement]:
    result = await db.execute(
        select(BodyMeasurement)
        .where(BodyMeasurement.customer_id == customer.id)
        .order_by(BodyMeasurement.recorded_at, BodyMeasurement.created_at)
    )
    return list(result.scalars().all())


@router.post("", response_model=MeasurementResponse, status_code=201)
async def log_measurement(
    payload: MeasurementCreate,
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> BodyMeasurement:
    values = payload.model_dump(exclude={"recorded_at"})
    entry = measurement_from(customer, values, payload.recorded_at)

    latest = await db.scalar(
        select(func.max(BodyMeasurement.recorded_at)).where(
            BodyMeasurement.customer_id == customer.id
        )
    )
    # Back-dated entries fill in history without overwriting the current profile.
    if latest is None or _as_utc(entry.recorded_at) >= _as_utc(latest):
        for field, value in values.items():
            if value is not None:
                setattr(customer, field, value)

    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry
