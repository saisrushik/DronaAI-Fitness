"""Deterministic health calculations (BRD section 5). No LLM involved."""

import math

ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

# Daily calorie adjustment against TDEE (BRD 4.1.4 and 5.4).
GOAL_CALORIE_DELTA = {
    "lose_fat": -400,  # middle of the 300-500 kcal deficit band
    "lean_bulk": 250,
    "aggressive_bulk": 500,
    "maintain": 0,
    "recomp": 0,
    "general_fitness": 0,
    "endurance": 0,  # fuelled through extra carbs instead (see GOAL_FAT_SHARE)
    "strength": 150,  # middle of the 100-200 kcal surplus band
}

# Protein grams per kg of body weight, mid-point of each BRD 5.5 range.
GOAL_PROTEIN_PER_KG = {
    "lose_fat": 2.2,
    "lean_bulk": 2.0,
    "aggressive_bulk": 2.0,
    "maintain": 1.6,
    "recomp": 2.4,
    "general_fitness": 1.6,
    "endurance": 1.6,
    "strength": 1.8,
}

# Safety floor for daily calories (BRD 5.4).
CALORIE_FLOOR = {"male": 1500, "female": 1200, "other": 1300}

FAT_CALORIE_SHARE = 0.25
# Endurance shifts calories from fat to carbs; still inside the BRD's 20-35% fat range.
GOAL_FAT_SHARE = {"endurance": 0.20}
MIN_FAT_PER_KG = 0.8
# Energy in one kilogram of body weight change, the usual rule of thumb.
KCAL_PER_KG = 7700

HEART_RATE_ZONES = [
    ("Zone 1 — Recovery", 0.50, 0.60),
    ("Zone 2 — Aerobic base", 0.60, 0.70),
    ("Zone 3 — Aerobic", 0.70, 0.80),
    ("Zone 4 — Threshold", 0.80, 0.90),
    ("Zone 5 — Anaerobic", 0.90, 1.00),
]


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    return round(weight_kg / (height_cm / 100) ** 2, 1)


def classify_bmi_who(bmi: float) -> str:
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal"
    if bmi < 30:
        return "Overweight"
    if bmi < 35:
        return "Obese class I"
    if bmi < 40:
        return "Obese class II"
    return "Obese class III"


def classify_bmi_asian(bmi: float) -> str:
    """Asian/Indian cut-offs, which are lower than the WHO thresholds."""
    if bmi < 18.5:
        return "Underweight"
    if bmi < 23:
        return "Normal"
    if bmi < 25:
        return "Overweight"
    if bmi < 30:
        return "Obese class I"
    return "Obese class II"


def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """Mifflin-St Jeor equation."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return round(base + 5 if gender == "male" else base - 161)


def calculate_tdee(bmr: float, activity_level: str) -> float:
    return round(bmr * ACTIVITY_MULTIPLIERS.get(activity_level, 1.2))


def calculate_body_fat(
    gender: str, height_cm: float, waist_cm: float | None, neck_cm: float | None,
    hip_cm: float | None
) -> float | None:
    """US Navy method. Needs waist and neck, plus hip for women."""
    if not waist_cm or not neck_cm:
        return None

    if gender == "female":
        if not hip_cm:
            return None
        inner = waist_cm + hip_cm - neck_cm
        if inner <= 0:
            return None
        value = (
            495
            / (
                1.29579
                - 0.35004 * math.log10(inner)
                + 0.22100 * math.log10(height_cm)
            )
            - 450
        )
    else:
        inner = waist_cm - neck_cm
        if inner <= 0:
            return None
        value = (
            495
            / (
                1.0324
                - 0.19077 * math.log10(inner)
                + 0.15456 * math.log10(height_cm)
            )
            - 450
        )

    return round(value, 1) if 0 < value < 70 else None


def classify_body_fat(gender: str, body_fat: float) -> str:
    if gender == "female":
        bounds = [(13, "Essential fat"), (20, "Athlete"), (24, "Fitness"), (31, "Average")]
    else:
        bounds = [(5, "Essential fat"), (13, "Athlete"), (17, "Fitness"), (24, "Average")]
    for limit, label in bounds:
        if body_fat <= limit:
            return label
    return "Obese"


def calculate_lbm(weight_kg: float, height_cm: float, gender: str) -> float:
    """Boer formula."""
    if gender == "female":
        return round(0.252 * weight_kg + 0.473 * height_cm - 48.3, 1)
    return round(0.407 * weight_kg + 0.267 * height_cm - 19.2, 1)


def calculate_ideal_weight(height_cm: float, gender: str) -> float:
    """Devine formula."""
    inches_over_5ft = max(0.0, height_cm / 2.54 - 60)
    base = 45.5 if gender == "female" else 50.0
    return round(base + 2.3 * inches_over_5ft, 1)


def healthy_weight_range(height_cm: float) -> dict:
    metres_squared = (height_cm / 100) ** 2
    return {
        "who": [round(18.5 * metres_squared, 1), round(24.9 * metres_squared, 1)],
        "asian": [round(18.5 * metres_squared, 1), round(22.9 * metres_squared, 1)],
    }


def heart_rate_zones(age: int) -> dict:
    """Tanaka formula for max heart rate."""
    hr_max = round(208 - 0.7 * age)
    return {
        "max": hr_max,
        "zones": [
            {"name": name, "low": round(hr_max * low), "high": round(hr_max * high)}
            for name, low, high in HEART_RATE_ZONES
        ],
    }


def calculate_targets(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    activity_level: str,
    goal: str,
    adjustment: int = 0,
) -> dict:
    """Flat calorie/macro targets used by the plan generator.

    `adjustment` is the coach's correction from weekly reviews; the safety floor still wins.
    """
    bmr = calculate_bmr(weight_kg, height_cm, age, gender)
    tdee = calculate_tdee(bmr, activity_level)
    floor = CALORIE_FLOOR.get(gender, 1300)
    goal_delta = GOAL_CALORIE_DELTA.get(goal, 0)
    calories = max(floor, round(tdee + goal_delta + adjustment))

    protein_g = round(weight_kg * GOAL_PROTEIN_PER_KG.get(goal, 1.6))
    fat_share = GOAL_FAT_SHARE.get(goal, FAT_CALORIE_SHARE)
    fat_g = round(max(calories * fat_share / 9, weight_kg * MIN_FAT_PER_KG))
    carbs_g = max(0, round((calories - protein_g * 4 - fat_g * 9) / 4))

    return {
        "bmi": calculate_bmi(weight_kg, height_cm),
        "bmr": bmr,
        "tdee": tdee,
        "target_calories": calories,
        "protein_g": protein_g,
        "carbs_g": carbs_g,
        "fat_g": fat_g,
        "calorie_floor_applied": calories == floor,
        "goal_delta": goal_delta,
        "adjustment": adjustment,
        "calorie_floor": floor,
    }


def expected_weekly_change_kg(goal: str) -> float:
    """Weight change per week the goal's calorie delta should produce (~7700 kcal per kg)."""
    return round(GOAL_CALORIE_DELTA.get(goal, 0) * 7 / KCAL_PER_KG, 2)


def calculate_metrics(
    *,
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    activity_level: str,
    goal: str,
    waist_cm: float | None = None,
    neck_cm: float | None = None,
    hip_cm: float | None = None,
    country: str = "IN",
    adjustment: int = 0,
) -> dict:
    """Everything shown on the health metrics dashboard."""
    targets = calculate_targets(
        weight_kg, height_cm, age, gender, activity_level, goal, adjustment
    )
    bmi = targets["bmi"]
    body_fat = calculate_body_fat(gender, height_cm, waist_cm, neck_cm, hip_cm)

    return {
        # The numbers each formula used, so the UI can explain every result (FR-8.1).
        "inputs": {
            "weight_kg": weight_kg,
            "height_cm": height_cm,
            "age": age,
            "gender": gender,
            "activity_level": activity_level,
            "activity_multiplier": ACTIVITY_MULTIPLIERS.get(activity_level, 1.2),
            "goal": goal,
            "protein_per_kg": GOAL_PROTEIN_PER_KG.get(goal, 1.6),
            "fat_share": GOAL_FAT_SHARE.get(goal, FAT_CALORIE_SHARE),
            "waist_cm": waist_cm,
            "neck_cm": neck_cm,
            "hip_cm": hip_cm,
        },
        "calorie_breakdown": {
            "tdee": targets["tdee"],
            "goal_delta": targets["goal_delta"],
            "coach_adjustment": targets["adjustment"],
            "floor": targets["calorie_floor"],
            "target": targets["target_calories"],
            "expected_weekly_change_kg": expected_weekly_change_kg(goal),
        },
        "bmi": {
            "value": bmi,
            "who": classify_bmi_who(bmi),
            "asian": classify_bmi_asian(bmi),
            # BRD 5.1: Indian users get the Asian cut-offs by default; both are always shown.
            "primary": "asian" if country.upper() == "IN" else "who",
        },
        "bmr": targets["bmr"],
        "tdee": targets["tdee"],
        "target_calories": targets["target_calories"],
        "calorie_floor_applied": targets["calorie_floor_applied"],
        "macros": {
            "protein_g": targets["protein_g"],
            "carbs_g": targets["carbs_g"],
            "fat_g": targets["fat_g"],
        },
        "body_fat": (
            {"value": body_fat, "category": classify_body_fat(gender, body_fat)}
            if body_fat is not None
            else None
        ),
        "lean_body_mass": calculate_lbm(weight_kg, height_cm, gender),
        "ideal_weight": calculate_ideal_weight(height_cm, gender),
        "healthy_weight": healthy_weight_range(height_cm),
        "heart_rate": heart_rate_zones(age),
    }
