"""Rule-based plan generation. The AI agent layer will replace this later."""

import copy

from app.db.models import Customer
from app.services.calculator import calculate_targets
from app.services.food_catalog import (
    FOODS,
    MEAL_OPTIONS,
    SESSION_CALORIE_SHARE,
    SESSIONS,
    WEEKDAYS,
)

# Training sessions for each goal, most important first. Fewer training days keep the first
# sessions; more days than listed repeat the list from the start.
GOAL_SESSIONS: dict[str, list[tuple[str, list[str]]]] = {
    "lose_fat": [
        ("Full body + conditioning", ["Goblet squat", "Push-ups", "Kettlebell swings"]),
        ("Cardio intervals", ["Bike sprints", "Rowing intervals", "Plank"]),
        ("Full body strength", ["Deadlift", "Dumbbell press", "Lat pulldown"]),
        ("Steady-state cardio", ["Incline walk", "Cycling", "Core circuit"]),
    ],
    "lean_bulk": [
        ("Upper body — push", ["Bench press", "Overhead press", "Triceps pushdown"]),
        ("Lower body", ["Back squat", "Romanian deadlift", "Calf raise"]),
        ("Upper body — pull", ["Pull-ups", "Barbell row", "Barbell curl"]),
        ("Full body", ["Deadlift", "Dumbbell thrusters", "Face pulls"]),
    ],
    "aggressive_bulk": [
        ("Chest & triceps", ["Bench press", "Incline dumbbell press", "Triceps pushdown"]),
        ("Back & biceps", ["Barbell row", "Lat pulldown", "Barbell curl"]),
        ("Legs", ["Back squat", "Romanian deadlift", "Leg press"]),
        ("Shoulders & arms", ["Overhead press", "Lateral raise", "Hammer curl"]),
        ("Full body", ["Deadlift", "Dumbbell thrusters", "Face pulls"]),
    ],
    "maintain": [
        ("Full body A", ["Back squat", "Bench press", "Barbell row"]),
        ("Full body B", ["Deadlift", "Overhead press", "Pull-ups"]),
        ("Full body + core", ["Lunges", "Dumbbell press", "Plank"]),
    ],
    "recomp": [
        ("Upper body strength", ["Bench press", "Barbell row", "Overhead press"]),
        ("Lower body strength", ["Back squat", "Romanian deadlift", "Calf raise"]),
        ("Conditioning", ["Kettlebell swings", "Rowing intervals", "Plank"]),
        ("Full body hypertrophy", ["Dumbbell press", "Lat pulldown", "Lunges"]),
    ],
    "general_fitness": [
        ("Full body strength", ["Goblet squat", "Push-ups", "Dumbbell row"]),
        ("Cardio & mobility", ["Brisk walk", "Cycling", "Mobility work"]),
        ("Full body + core", ["Lunges", "Dumbbell press", "Plank"]),
    ],
    "endurance": [
        ("Tempo run", ["Warm-up jog", "Tempo intervals", "Cool-down"]),
        ("Strength support", ["Back squat", "Step-ups", "Core circuit"]),
        ("Long intervals", ["400m repeats", "Hill sprints", "Stretching"]),
        ("Long slow distance", ["Steady run", "Mobility work"]),
    ],
    "strength": [
        ("Squat focus", ["Back squat", "Romanian deadlift", "Plank"]),
        ("Bench focus", ["Bench press", "Barbell row", "Triceps pushdown"]),
        ("Deadlift focus", ["Deadlift", "Pull-ups", "Face pulls"]),
        ("Overhead focus", ["Overhead press", "Lat pulldown", "Barbell curl"]),
    ],
}

# Spread across the week with rest days in between where possible.
TRAINING_WEEKDAYS = {
    2: ["Monday", "Thursday"],
    3: ["Monday", "Wednesday", "Friday"],
    4: ["Monday", "Tuesday", "Thursday", "Saturday"],
    5: ["Monday", "Tuesday", "Wednesday", "Friday", "Saturday"],
    6: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
}

# Base sets and rep range for an intermediate lifter.
GOAL_VOLUME = {
    "lose_fat": (3, "12–15"),
    "lean_bulk": (4, "6–10"),
    "aggressive_bulk": (4, "6–10"),
    "maintain": (3, "10–12"),
    "recomp": (3, "8–12"),
    "general_fitness": (3, "10–12"),
    "endurance": (3, "15–20"),
    "strength": (4, "3–5"),
}
EXPERIENCE_SETS = {"beginner": -1, "intermediate": 0, "advanced": 1}
MIN_SETS, MAX_SETS = 2, 5

# Gym exercises and the bodyweight or resistance-band version used for home training.
HOME_ALTERNATIVES = {
    "Bench press": "Push-ups",
    "Dumbbell press": "Push-ups",
    "Incline dumbbell press": "Decline push-ups",
    "Overhead press": "Pike push-ups",
    "Triceps pushdown": "Bench dips",
    "Lat pulldown": "Resistance band pulldown",
    "Pull-ups": "Inverted table rows",
    "Barbell row": "Backpack rows",
    "Dumbbell row": "Backpack rows",
    "Barbell curl": "Resistance band curl",
    "Hammer curl": "Resistance band hammer curl",
    "Lateral raise": "Resistance band lateral raise",
    "Face pulls": "Resistance band face pulls",
    "Back squat": "Bodyweight squat",
    "Goblet squat": "Bodyweight squat",
    "Leg press": "Bulgarian split squat",
    "Romanian deadlift": "Single-leg RDL",
    "Deadlift": "Glute bridge",
    "Kettlebell swings": "Jump squats",
    "Dumbbell thrusters": "Burpees",
    "Bike sprints": "High-knee sprints",
    "Rowing intervals": "Mountain climbers",
    "Incline walk": "Brisk walk",
}

_SPINE = {
    "Deadlift",
    "Romanian deadlift",
    "Barbell row",
    "Back squat",
    "Kettlebell swings",
    "Single-leg RDL",
    "Backpack rows",
}
# Exercises removed for an injury to each body part (BRD 4.1.6 body parts).
INJURY_EXCLUSIONS: dict[str, set[str]] = {
    "knee": {
        "Back squat",
        "Goblet squat",
        "Bodyweight squat",
        "Leg press",
        "Lunges",
        "Bulgarian split squat",
        "Step-ups",
        "Jump squats",
        "Burpees",
        "Hill sprints",
        "High-knee sprints",
    },
    "lower_back": _SPINE,
    "upper_back": _SPINE | {"Pull-ups", "Inverted table rows"},
    "shoulder": {
        "Overhead press",
        "Pike push-ups",
        "Bench press",
        "Dumbbell press",
        "Incline dumbbell press",
        "Push-ups",
        "Decline push-ups",
        "Pull-ups",
        "Lateral raise",
        "Resistance band lateral raise",
        "Bench dips",
        "Burpees",
    },
    "elbow": {
        "Triceps pushdown",
        "Bench dips",
        "Barbell curl",
        "Hammer curl",
        "Resistance band curl",
        "Resistance band hammer curl",
    },
    "wrist": {
        "Push-ups",
        "Decline push-ups",
        "Pike push-ups",
        "Burpees",
        "Bench dips",
        "Mountain climbers",
        "Barbell curl",
    },
    "hip": {
        "Back squat",
        "Deadlift",
        "Romanian deadlift",
        "Single-leg RDL",
        "Lunges",
        "Bulgarian split squat",
        "Step-ups",
        "Kettlebell swings",
        "Hill sprints",
    },
    "ankle": {
        "Jump squats",
        "Burpees",
        "Hill sprints",
        "High-knee sprints",
        "400m repeats",
        "Tempo intervals",
        "Steady run",
        "Warm-up jog",
        "Lunges",
        "Calf raise",
    },
    "neck": {"Overhead press", "Pike push-ups", "Back squat"},
    "other": set(),
}

CONDITION_LABELS = {
    "hypertension": "high blood pressure",
    "diabetes": "diabetes",
    "heart_condition": "a heart condition",
    "pcos": "PCOS",
    "thyroid": "a thyroid condition",
    "asthma": "asthma",
    "pregnancy": "pregnancy",
    "other": "a medical condition",
}


def _matches(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def medical_note(customer: Customer) -> str:
    """BRD 4.1.6: declared conditions trigger a medical disclaimer on every plan."""
    conditions = customer.medical_conditions or []
    if not conditions:
        return ""
    named = ", ".join(CONDITION_LABELS.get(c, c) for c in conditions)
    return (
        f" Medical conditions on file ({named}): this plan is general guidance, not medical "
        "advice. Check it with your doctor before starting."
    )


def _injured_parts(customer: Customer) -> list[str]:
    parts = [injury.get("body_part", "other") for injury in customer.injuries or []]
    return list(dict.fromkeys(parts))


def generate_workout_plan(customer: Customer) -> dict:
    goal = customer.primary_goal if customer.primary_goal in GOAL_SESSIONS else "maintain"
    sessions = GOAL_SESSIONS[goal]
    days_per_week = customer.training_days_per_week or len(sessions)
    days_per_week = min(max(days_per_week, 2), 6)
    experience = customer.training_experience or "intermediate"
    location = customer.training_location or "gym"
    high_stress = customer.stress_level == "high"

    base_sets, reps = GOAL_VOLUME[goal]
    sets = base_sets + EXPERIENCE_SETS.get(experience, 0) - (1 if high_stress else 0)
    sets = min(max(sets, MIN_SETS), MAX_SETS)

    parts = _injured_parts(customer)
    excluded_pool = set().union(*(INJURY_EXCLUSIONS.get(p, set()) for p in parts))

    days = []
    excluded: set[str] = set()
    for index, weekday in enumerate(TRAINING_WEEKDAYS[days_per_week]):
        focus, exercises = sessions[index % len(sessions)]
        if location == "home":
            exercises = [HOME_ALTERNATIVES.get(e, e) for e in exercises]
        exercises = list(dict.fromkeys(exercises))
        safe = [e for e in exercises if e not in excluded_pool]
        removed = [e for e in exercises if e in excluded_pool]
        excluded.update(removed)
        days.append(
            {
                "day": weekday,
                "focus": focus,
                "exercises": [{"name": e, "sets": sets, "reps": reps} for e in safe],
                "removed_for_safety": removed,
            }
        )

    notes = [
        f"{days_per_week} training days a week, {sets} sets per exercise "
        f"for your {experience} level."
    ]
    if high_stress:
        notes.append("One set removed from every exercise because stress is high.")
    if location == "home":
        notes.append("Home version: gym lifts are swapped for bodyweight and band exercises.")
    if excluded:
        named_parts = ", ".join(p.replace("_", " ") for p in parts)
        notes.append(
            f"Exercises excluded due to injury history ({named_parts}): "
            f"{', '.join(sorted(excluded))}."
        )
    elif parts and set(parts) != {"other"}:
        notes.append("No exercises in this plan load the injured areas on file.")
    else:
        notes.append("No exercises excluded — no relevant injury history on file.")
    if "other" in parts:
        notes.append("An injury marked 'other' is on file; your coach should review exercise choice.")

    return {
        "goal": goal,
        "days_per_week": days_per_week,
        "experience": experience,
        "location": location,
        "days": days,
        "notes": " ".join(notes) + medical_note(customer),
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
        adjustment=customer.calorie_adjustment or 0,
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
        + (f", avoiding: {avoided}." if avoided else ".")
        + medical_note(customer),
    }


def find_meal(content: dict, day: str, session: str) -> dict | None:
    for plan_day in content.get("days", []):
        if plan_day["day"] == day:
            return next((s for s in plan_day["sessions"] if s["name"] == session), None)
    return None


def _food_key(name: str) -> str:
    return name.strip().lower()


def meal_diff(current_items: list[dict], wanted: list[str]) -> tuple[list[dict], list[str], list[str]]:
    """Splits a requested food list into kept items (with nutrition), added names and removed names."""
    current = {_food_key(item["name"]): item for item in current_items}
    wanted_keys = {_food_key(name) for name in wanted}

    kept: list[dict] = []
    added: list[str] = []
    seen: set[str] = set()
    for name in wanted:
        key = _food_key(name)
        if key in seen:
            continue
        seen.add(key)
        if key in current:
            kept.append(current[key])
        else:
            added.append(name)
    removed = [item["name"] for item in current_items if _food_key(item["name"]) not in wanted_keys]
    return kept, added, removed


def _recalculate(content: dict) -> None:
    week_totals = _empty_totals()
    for plan_day in content["days"]:
        day_totals = _empty_totals()
        for session in plan_day["sessions"]:
            _add(day_totals, session["totals"])
        plan_day["totals"] = _rounded(day_totals)
        _add(week_totals, day_totals)

    content["weekly_totals"] = _rounded(week_totals)
    content["daily_average"] = _rounded(
        {k: v / max(1, len(content["days"])) for k, v in week_totals.items()}
    )


def apply_meal_changes(content: dict, meals: list[dict], option: str = "Your choice") -> dict:
    """Returns a copy of a diet plan with the given meals replaced and every total recalculated."""
    updated = copy.deepcopy(content)
    for meal in meals:
        session = find_meal(updated, meal["day"], meal["session"])
        if session is None:
            raise ValueError(f"{meal['day']} {meal['session']} is not in this plan")
        totals = _empty_totals()
        for item in meal["items"]:
            _add(totals, item)
        session["items"] = [{**item, **_rounded(item)} for item in meal["items"]]
        session["option"] = option
        session["totals"] = _rounded(totals)

    _recalculate(updated)
    return updated


def remove_meal(content: dict, day: str, session: str) -> dict:
    """Returns a copy of a diet plan without the given meal, with totals recalculated."""
    if find_meal(content, day, session) is None:
        raise ValueError(f"{day} {session} is not in this plan")
    updated = copy.deepcopy(content)
    for plan_day in updated["days"]:
        if plan_day["day"] == day:
            plan_day["sessions"] = [s for s in plan_day["sessions"] if s["name"] != session]
    _recalculate(updated)
    return updated
