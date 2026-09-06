"""Rule-based plan generation. The AI agent layer will replace this later."""

from app.db.models import Customer
from app.services.calculator import calculate_targets
from app.services.food_catalog import (
    FOODS,
    MEAL_OPTIONS,
    SESSION_CALORIE_SHARE,
    SESSIONS,
    WEEKDAYS,
)

WORKOUT_SPLITS = {
    "lose_fat": [
        ("Monday", "Full body + conditioning", ["Goblet squat", "Push-ups", "Kettlebell swings"]),
        ("Tuesday", "Cardio intervals", ["Bike sprints", "Rowing intervals", "Plank"]),
        ("Thursday", "Full body strength", ["Deadlift", "Dumbbell press", "Lat pulldown"]),
        ("Saturday", "Steady-state cardio", ["Incline walk", "Cycling", "Core circuit"]),
    ],
    "build_muscle": [
        ("Monday", "Upper body — push", ["Bench press", "Overhead press", "Triceps pushdown"]),
        ("Tuesday", "Lower body", ["Back squat", "Romanian deadlift", "Calf raise"]),
        ("Thursday", "Upper body — pull", ["Pull-ups", "Barbell row", "Barbell curl"]),
        ("Saturday", "Full body", ["Deadlift", "Dumbbell thrusters", "Face pulls"]),
    ],
    "maintain": [
        ("Monday", "Full body", ["Squat", "Bench press", "Barbell row"]),
        ("Wednesday", "Full body", ["Deadlift", "Overhead press", "Pull-ups"]),
        ("Friday", "Full body + core", ["Lunges", "Dumbbell press", "Plank"]),
    ],
    "improve_endurance": [
        ("Monday", "Tempo run", ["Warm-up jog", "Tempo intervals", "Cool-down"]),
        ("Wednesday", "Strength support", ["Squat", "Step-ups", "Core circuit"]),
        ("Friday", "Long intervals", ["400m repeats", "Hill sprints", "Stretching"]),
        ("Sunday", "Long slow distance", ["Steady run", "Mobility work"]),
    ],
}

SETS_REPS = {
    "lose_fat": (3, "12–15"),
    "build_muscle": (4, "6–10"),
    "maintain": (3, "10–12"),
    "improve_endurance": (3, "15–20"),
}

# Exercises to avoid when an injury keyword appears in the customer's history.
INJURY_EXCLUSIONS = {
    "back": ["Deadlift", "Romanian deadlift", "Barbell row", "Back squat"],
    "knee": ["Back squat", "Lunges", "Step-ups", "Hill sprints", "Goblet squat"],
    "shoulder": ["Overhead press", "Bench press", "Dumbbell press", "Pull-ups"],
}

def _matches(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def generate_workout_plan(customer: Customer) -> dict:
    goal = customer.primary_goal or "maintain"
    split = WORKOUT_SPLITS.get(goal, WORKOUT_SPLITS["maintain"])
    sets, reps = SETS_REPS.get(goal, SETS_REPS["maintain"])

    injuries = " ".join(customer.health_injury_history or []).lower()
    excluded = {
        exercise
        for keyword, exercises in INJURY_EXCLUSIONS.items()
        if keyword in injuries
        for exercise in exercises
    }

    days = []
    for day, focus, exercises in split:
        safe = [e for e in exercises if e not in excluded]
        substitutions = [e for e in exercises if e in excluded]
        days.append(
            {
                "day": day,
                "focus": focus,
                "exercises": [{"name": e, "sets": sets, "reps": reps} for e in safe],
                "removed_for_safety": substitutions,
            }
        )

    return {
        "goal": goal,
        "days_per_week": len(split),
        "days": days,
        "notes": (
            f"Exercises excluded due to injury history: {', '.join(sorted(excluded))}."
            if excluded
            else "No exercises excluded — no relevant injury history on file."
        ),
    }


# Maps a phrase in dietary_preferences to the food tag that must be avoided.
ALLERGEN_KEYWORDS = {
    "dairy": ["no dairy", "dairy free", "dairy-free", "lactose"],
    "peanut": ["peanut"],
    "nuts": ["nut allergy", "tree nut", "no nuts"],
    "gluten": ["gluten", "celiac", "coeliac"],
    "egg": ["no egg", "egg allergy", "eggless"],
    "soy": ["no soy", "soy allergy"],
    "fish": ["no fish", "pescatarian-free", "fish allergy"],
}

STYLE_ALLOWED_DIETS = {
    "vegan": {"vegan"},
    "vegetarian": {"vegan", "vegetarian"},
    "eggetarian": {"vegan", "vegetarian", "eggetarian"},
    "non_vegetarian": {"vegan", "vegetarian", "eggetarian", "non_vegetarian"},
}


def _empty_totals() -> dict:
    return {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}


def _add(totals: dict, other: dict) -> None:
    for key in totals:
        totals[key] += other[key]


def _rounded(totals: dict) -> dict:
    return {
        "calories": round(totals["calories"]),
        "protein_g": round(totals["protein_g"]),
        "carbs_g": round(totals["carbs_g"]),
        "fat_g": round(totals["fat_g"]),
    }


def _build_session(session: str, option: dict, target_calories: float) -> dict:
    base = sum(FOODS[item]["cal"] for item in option["items"])
    # Keep portions realistic rather than matching the target exactly.
    scale = min(2.0, max(0.5, target_calories / base)) if base else 1.0

    items = []
    totals = _empty_totals()
    for item in option["items"]:
        food = FOODS[item]
        macros = {
            "calories": food["cal"] * scale,
            "protein_g": food["p"] * scale,
            "carbs_g": food["c"] * scale,
            "fat_g": food["f"] * scale,
        }
        _add(totals, macros)
        quantity = food["qty"] * scale
        items.append(
            {
                "name": item,
                "quantity": f"{quantity:.0f} {food['unit']}"
                if quantity >= 10
                else f"{quantity:.1f} {food['unit']}",
                **_rounded(macros),
            }
        )

    return {"name": session, "option": option["name"], "items": items, "totals": _rounded(totals)}


def generate_diet_plan(customer: Customer) -> dict:
    targets = calculate_targets(
        weight_kg=customer.weight_kg or 70,
        height_cm=customer.height_cm or 170,
        age=customer.age or 30,
        gender=customer.gender or "male",
        activity_level=customer.activity_level or "moderate",
        goal=customer.primary_goal or "maintain",
    )

    prefs = " ".join(customer.dietary_preferences or []).lower()
    style = customer.diet_type or "non_vegetarian"

    avoided_tags = {
        tag for tag, keywords in ALLERGEN_KEYWORDS.items() if _matches(prefs, keywords)
    }
    allowed_diets = STYLE_ALLOWED_DIETS[style]

    def usable(session: str) -> list[dict]:
        by_style = [o for o in MEAL_OPTIONS[session] if o["diet"] in allowed_diets]
        safe = [
            o
            for o in by_style
            if not any(FOODS[i]["tags"] & avoided_tags for i in o["items"])
        ]
        return safe or by_style

    options_by_session = {session: usable(session) for session in SESSIONS}
    calories = targets["target_calories"]

    days = []
    week_totals = _empty_totals()
    for day_index, weekday in enumerate(WEEKDAYS):
        sessions = []
        day_totals = _empty_totals()
        for session_index, session in enumerate(SESSIONS):
            choices = options_by_session[session]
            option = choices[(day_index + session_index) % len(choices)]
            built = _build_session(session, option, calories * SESSION_CALORIE_SHARE[session])
            sessions.append(built)
            _add(day_totals, built["totals"])

        _add(week_totals, day_totals)
        days.append({"day": weekday, "sessions": sessions, "totals": _rounded(day_totals)})

    avoided = ", ".join(sorted(avoided_tags))
    return {
        "style": style.replace("_", " "),
        "targets": targets,
        "days": days,
        "weekly_totals": _rounded(week_totals),
        "daily_average": _rounded({k: v / 7 for k, v in week_totals.items()}),
        "notes": f"7-day {style.replace('_', ' ')} plan at roughly {calories} kcal per day"
        + (f", avoiding: {avoided}." if avoided else "."),
    }
