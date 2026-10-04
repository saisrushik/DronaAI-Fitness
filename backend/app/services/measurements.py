from datetime import datetime, timezone

from app.db.models import BodyMeasurement, Customer

BODY_FIELDS = ("weight_kg", "height_cm", "waist_cm", "neck_cm", "hip_cm")


def body_values(customer: Customer) -> dict[str, float | None]:
    return {field: getattr(customer, field) for field in BODY_FIELDS}


def measurement_from(
    customer: Customer, values: dict[str, float | None], recorded_at: datetime | None = None
) -> BodyMeasurement | None:
    """Builds a log entry for the non-empty values, or None when there is nothing to log."""
    logged = {field: values.get(field) for field in BODY_FIELDS}
    if all(value is None for value in logged.values()):
        return None
    return BodyMeasurement(
        customer_id=customer.id,
        recorded_at=recorded_at or datetime.now(timezone.utc),
        **logged,
    )


def changed_values(
    before: dict[str, float | None], after: dict[str, float | None]
) -> dict[str, float | None]:
    return {field: after[field] for field in BODY_FIELDS if after[field] != before[field]}
