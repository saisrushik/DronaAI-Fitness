"""Safety behaviour of the rule-based generators."""

from datetime import date

import pytest

from app.db.models import Customer
from app.services.plan_generator import generate_diet_plan, generate_workout_plan


def make_customer(**overrides) -> Customer:
    defaults = {
        "date_of_birth": date(1994, 3, 15),
        "gender": "male",
        "height_cm": 180.0,
        "weight_kg": 85.0,
        "activity_level": "moderate",
        "primary_goal": "lean_bulk",
        "diet_type": "non_vegetarian",
        "dietary_preferences": [],
        "injuries": [],
    }
    return Customer(**{**defaults, **overrides})


def injury(body_part: str, **details) -> dict:
    return {"body_part": body_part, "severity": "moderate", "recovery_status": "recovering",
            "date_of_injury": None, "notes": "", **details}


def exercise_names(plan: dict) -> list[str]:
    return [e["name"] for day in plan["days"] for e in day["exercises"]]


def test_knee_injury_removes_knee_loading_exercises():
    plan = generate_workout_plan(make_customer(injuries=[injury("knee")]))
    exercises = exercise_names(plan)

    assert "Back squat" not in exercises
    assert "Lunges" not in exercises
    assert "Back squat" in plan["notes"]


def test_back_injury_removes_spinal_loading_exercises():
    plan = generate_workout_plan(make_customer(injuries=[injury("lower_back")]))
    exercises = exercise_names(plan)

    assert "Deadlift" not in exercises
    assert "Barbell row" not in exercises


def test_no_injuries_keeps_full_programme():
    plan = generate_workout_plan(make_customer())

    assert "Back squat" in exercise_names(plan)
    assert "No exercises excluded" in plan["notes"]


@pytest.mark.parametrize(
    "goal",
    ["lose_fat", "lean_bulk", "aggressive_bulk", "maintain", "recomp", "general_fitness",
     "endurance", "strength"],
)
def test_every_brd_goal_gets_its_own_programme(goal):
    plan = generate_workout_plan(make_customer(primary_goal=goal))
    assert plan["goal"] == goal
    assert plan["days"] and all(day["exercises"] for day in plan["days"])


def test_strength_uses_low_reps_and_endurance_high_reps():
    strength = generate_workout_plan(make_customer(primary_goal="strength"))
    endurance = generate_workout_plan(make_customer(primary_goal="endurance"))
    assert strength["days"][0]["exercises"][0]["reps"] == "3–5"
    assert endurance["days"][0]["exercises"][0]["reps"] == "15–20"


@pytest.mark.parametrize(
    ("days", "weekdays"),
    [(2, ["Monday", "Thursday"]), (6, ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])],
)
def test_training_days_per_week_shapes_the_split(days, weekdays):
    plan = generate_workout_plan(make_customer(training_days_per_week=days))
    assert plan["days_per_week"] == days
    assert [day["day"] for day in plan["days"]] == weekdays


def _sets(**overrides) -> int:
    plan = generate_workout_plan(make_customer(**overrides))
    return plan["days"][0]["exercises"][0]["sets"]


def test_experience_and_stress_set_the_volume():
    # lean_bulk is 4 sets for an intermediate lifter.
    assert _sets(training_experience="intermediate") == 4
    assert _sets(training_experience="beginner") == 3
    assert _sets(training_experience="advanced") == 5
    assert _sets(training_experience="intermediate", stress_level="high") == 3
    assert _sets(training_experience="beginner", stress_level="high", primary_goal="maintain") == 2


def test_home_training_swaps_gym_lifts_for_bodyweight():
    plan = generate_workout_plan(make_customer(training_location="home"))
    exercises = exercise_names(plan)

    assert "Bench press" not in exercises
    assert "Push-ups" in exercises
    assert "Home version" in plan["notes"]


def test_injuries_also_filter_home_exercises():
    plan = generate_workout_plan(
        make_customer(training_location="home", injuries=[injury("knee")])
    )
    assert "Bodyweight squat" not in exercise_names(plan)


def test_medical_conditions_add_a_disclaimer_to_both_plans():
    customer = make_customer(medical_conditions=["hypertension"])
    assert "high blood pressure" in generate_workout_plan(customer)["notes"]
    assert "not medical advice" in generate_diet_plan(customer)["notes"]


def test_weekly_diet_plan_shape():
    plan = generate_diet_plan(make_customer())

    assert len(plan["days"]) == 7
    for day in plan["days"]:
        assert [s["name"] for s in day["sessions"]] == ["Breakfast", "Lunch", "Snack", "Dinner"]


@pytest.mark.parametrize(
    ("diet_type", "banned"),
    [
        ("vegan", {"Chicken breast", "Salmon fillet", "Eggs", "Milk", "Greek yoghurt", "Paneer"}),
        ("vegetarian", {"Chicken breast", "Salmon fillet", "Tuna", "Lean beef", "Eggs"}),
        ("eggetarian", {"Chicken breast", "Salmon fillet", "Tuna", "Lean beef"}),
    ],
)
def test_diet_type_is_respected(diet_type, banned):
    plan = generate_diet_plan(make_customer(diet_type=diet_type))
    items = {
        item["name"]
        for day in plan["days"]
        for session in day["sessions"]
        for item in session["items"]
    }
    assert not items & banned


def test_allergens_are_excluded():
    plan = generate_diet_plan(make_customer(dietary_preferences=["peanut allergy"]))
    items = {
        item["name"]
        for day in plan["days"]
        for session in day["sessions"]
        for item in session["items"]
    }
    assert "Peanut butter" not in items


def test_dairy_free_is_respected():
    plan = generate_diet_plan(make_customer(dietary_preferences=["no dairy"]))
    items = {
        item["name"]
        for day in plan["days"]
        for session in day["sessions"]
        for item in session["items"]
    }
    assert not items & {"Milk", "Greek yoghurt", "Cottage cheese", "Paneer", "Whey protein"}


def test_totals_add_up_across_levels():
    plan = generate_diet_plan(make_customer())

    for day in plan["days"]:
        session_protein = sum(s["totals"]["protein_g"] for s in day["sessions"])
        assert day["totals"]["protein_g"] == pytest.approx(session_protein, abs=2)

    week_calories = sum(day["totals"]["calories"] for day in plan["days"])
    assert plan["weekly_totals"]["calories"] == pytest.approx(week_calories, abs=7)


def test_menus_vary_across_the_week():
    plan = generate_diet_plan(make_customer())
    breakfasts = [day["sessions"][0]["option"] for day in plan["days"]]
    assert len(set(breakfasts)) > 1
