from app.db.models import Customer
from app.services.calculator import calculate_metrics


def metrics_for(customer: Customer | None) -> dict | None:
    """Full metric set, or None when the profile isn't complete enough to compute it."""
    if customer is None or not customer.profile_completed:
        return None
    if not all([customer.weight_kg, customer.height_cm, customer.age, customer.gender]):
        return None

    return calculate_metrics(
        weight_kg=customer.weight_kg,
        height_cm=customer.height_cm,
        age=customer.age,
        gender=customer.gender,
        activity_level=customer.activity_level or "moderate",
        goal=customer.primary_goal or "maintain",
        waist_cm=customer.waist_cm,
        neck_cm=customer.neck_cm,
        hip_cm=customer.hip_cm,
    )
