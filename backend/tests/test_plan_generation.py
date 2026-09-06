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
        "primary_goal": "build_muscle",
        "diet_type": "non_vegetarian",
        "dietary_preferences": [],
        "health_injury_history": [],
    }
    return Customer(**{**defaults, **overrides})


def test_knee_injury_removes_knee_loading_exercises():
    plan = generate_workout_plan(make_customer(health_injury_history=["knee surgery"]))
    exercises = [e["name"] for day in plan["days"] for e in day["exercises"]]

    assert "Back squat" not in exercises
    assert "Lunges" not in exercises
    assert "Back squat" in plan["notes"]


def test_back_injury_removes_spinal_loading_exercises():
    plan = generate_workout_plan(make_customer(health_injury_history=["lower back pain"]))
    exercises = [e["name"] for day in plan["days"] for e in day["exercises"]]

    assert "Deadlift" not in exercises
    assert "Barbell row" not in exercises


def test_no_injuries_keeps_full_programme():
    plan = generate_workout_plan(make_customer())
    exercises = [e["name"] for day in plan["days"] for e in day["exercises"]]

    assert "Back squat" in exercises
    assert "No exercises excluded" in plan["notes"]


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
