"""Values are cross-checked against the formulas in BRD section 5."""

import pytest

from app.services.calculator import (
    calculate_bmi,
    calculate_bmr,
    calculate_body_fat,
    calculate_ideal_weight,
    calculate_lbm,
    calculate_targets,
    calculate_tdee,
    classify_bmi_asian,
    classify_bmi_who,
    healthy_weight_range,
    heart_rate_zones,
)


def test_bmi():
    # 85 / 1.80^2 = 26.23
    assert calculate_bmi(85, 180) == 26.2


@pytest.mark.parametrize(
    ("bmi", "who", "asian"),
    [
        (17.0, "Underweight", "Underweight"),
        (22.0, "Normal", "Normal"),
        (24.0, "Normal", "Overweight"),  # Asian cut-off is stricter
        (27.0, "Overweight", "Obese class I"),
        (32.0, "Obese class I", "Obese class II"),
    ],
)
def test_bmi_classifications_differ_between_standards(bmi, who, asian):
    assert classify_bmi_who(bmi) == who
    assert classify_bmi_asian(bmi) == asian


def test_bmr_mifflin_st_jeor():
    # Male: 10(85) + 6.25(180) - 5(32) + 5 = 1820
    assert calculate_bmr(85, 180, 32, "male") == 1820
    # Female: same minus 161, minus the male +5 => 1654
    assert calculate_bmr(85, 180, 32, "female") == 1654


def test_tdee_applies_activity_multiplier():
    assert calculate_tdee(2000, "sedentary") == 2400  # 2000 * 1.2
    assert calculate_tdee(2000, "very_active") == 3800  # 2000 * 1.9


def test_body_fat_navy_method():
    male = calculate_body_fat("male", 180, waist_cm=94, neck_cm=40, hip_cm=None)
    assert male == pytest.approx(21.2, abs=0.3)

    female = calculate_body_fat("female", 163, waist_cm=72, neck_cm=32, hip_cm=96)
    assert female == pytest.approx(26.9, abs=0.3)


def test_body_fat_returns_none_without_measurements():
    assert calculate_body_fat("male", 180, None, None, None) is None
    # Women need a hip measurement for the Navy formula.
    assert calculate_body_fat("female", 163, 72, 32, None) is None


def test_lean_body_mass_boer():
    # 0.407(85) + 0.267(180) - 19.2 = 63.5
    assert calculate_lbm(85, 180, "male") == 63.5


def test_ideal_weight_devine():
    # 180cm = 70.87in -> 50 + 2.3(10.87) = 75.0
    assert calculate_ideal_weight(180, "male") == 75.0
    assert calculate_ideal_weight(180, "female") == 70.5


def test_healthy_weight_range_is_stricter_for_asian_standard():
    ranges = healthy_weight_range(180)
    assert ranges["who"] == [59.9, 80.7]
    assert ranges["asian"][1] < ranges["who"][1]


def test_heart_rate_zones_tanaka():
    zones = heart_rate_zones(30)
    assert zones["max"] == 187  # 208 - 0.7(30)
    assert len(zones["zones"]) == 5
    assert zones["zones"][0]["low"] == round(187 * 0.5)
    assert zones["zones"][-1]["high"] == 187


def test_calorie_floor_protects_against_extreme_deficits():
    # A small, sedentary woman aiming to lose fat would otherwise fall below the floor.
    targets = calculate_targets(45, 150, 60, "female", "sedentary", "lose_fat")
    assert targets["target_calories"] == 1200
    assert targets["calorie_floor_applied"] is True


def test_goal_shifts_calories_in_the_right_direction():
    args = (85, 180, 32, "male", "moderate")
    lose = calculate_targets(*args, "lose_fat")["target_calories"]
    maintain = calculate_targets(*args, "maintain")["target_calories"]
    gain = calculate_targets(*args, "build_muscle")["target_calories"]

    assert lose < maintain < gain


def test_macros_roughly_account_for_the_calorie_target():
    targets = calculate_targets(85, 180, 32, "male", "moderate", "lose_fat")
    from_macros = (
        targets["protein_g"] * 4 + targets["carbs_g"] * 4 + targets["fat_g"] * 9
    )
    assert from_macros == pytest.approx(targets["target_calories"], rel=0.02)


def test_higher_protein_for_fat_loss_than_maintenance():
    args = (85, 180, 32, "male", "moderate")
    assert (
        calculate_targets(*args, "lose_fat")["protein_g"]
        > calculate_targets(*args, "maintain")["protein_g"]
    )
