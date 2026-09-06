"""Food catalog used to build diet plans. Macros are per the listed base quantity."""


def _food(qty: float, unit: str, cal: float, p: float, c: float, f: float, *tags: str) -> dict:
    return {"qty": qty, "unit": unit, "cal": cal, "p": p, "c": c, "f": f, "tags": set(tags)}


FOODS: dict[str, dict] = {
    # --- Grains & starches ---
    "Rolled oats": _food(60, "g", 228, 8.4, 39, 4.2, "gluten"),
    "Brown rice (cooked)": _food(150, "g", 165, 3.8, 34, 1.3),
    "Quinoa (cooked)": _food(150, "g", 180, 6.6, 31, 2.9),
    "Whole-wheat bread": _food(2, "slices", 160, 8, 28, 2, "gluten"),
    "Whole-wheat pasta (cooked)": _food(150, "g", 190, 7.5, 38, 1.1, "gluten"),
    "Sweet potato": _food(200, "g", 172, 3.2, 40, 0.2),
    # --- Fruit ---
    "Banana": _food(1, "medium", 105, 1.3, 27, 0.4),
    "Apple": _food(1, "medium", 95, 0.5, 25, 0.3),
    "Mixed berries": _food(100, "g", 57, 0.7, 14, 0.3),
    # --- Animal protein ---
    "Chicken breast": _food(150, "g", 248, 46.5, 0, 5.4),
    "Salmon fillet": _food(150, "g", 280, 34, 0, 15, "fish"),
    "Tuna": _food(100, "g", 116, 26, 0, 1, "fish"),
    "Lean beef": _food(150, "g", 250, 39, 0, 10),
    "Eggs": _food(2, "large", 143, 12.6, 0.7, 9.5, "egg"),
    # --- Dairy ---
    "Milk": _food(250, "ml", 122, 8, 12, 4.8, "dairy"),
    "Greek yoghurt": _food(170, "g", 100, 17, 6, 0.7, "dairy"),
    "Cottage cheese": _food(150, "g", 145, 17, 5, 6, "dairy"),
    "Paneer": _food(100, "g", 265, 18, 3, 20, "dairy"),
    "Whey protein": _food(30, "g", 120, 24, 3, 1.5, "dairy"),
    # --- Plant protein ---
    "Firm tofu": _food(150, "g", 173, 18, 4, 10, "soy"),
    "Tempeh": _food(100, "g", 192, 20, 8, 11, "soy"),
    "Edamame": _food(100, "g", 121, 12, 9, 5, "soy"),
    "Soy milk": _food(250, "ml", 105, 8, 12, 3.5, "soy"),
    "Pea protein": _food(30, "g", 110, 24, 1, 2),
    "Chickpeas (cooked)": _food(150, "g", 246, 13, 41, 4),
    "Red lentils (cooked)": _food(150, "g", 175, 12, 30, 0.6),
    "Black beans (cooked)": _food(150, "g", 199, 13, 36, 0.9),
    # --- Fats ---
    "Almonds": _food(30, "g", 173, 6.3, 6, 15, "nuts"),
    "Mixed nuts": _food(30, "g", 180, 5, 7, 16, "nuts"),
    "Peanut butter": _food(30, "g", 188, 8, 6, 16, "peanut"),
    "Olive oil": _food(10, "ml", 88, 0, 0, 10),
    "Avocado": _food(100, "g", 160, 2, 9, 15),
    "Chia seeds": _food(20, "g", 97, 3.3, 8, 6),
    # --- Vegetables ---
    "Mixed vegetables": _food(200, "g", 80, 4, 16, 0.6),
    "Broccoli": _food(150, "g", 51, 4.2, 10, 0.6),
    "Spinach": _food(100, "g", 23, 2.9, 3.6, 0.4),
    "Salad greens": _food(100, "g", 20, 1.5, 3, 0.3),
}


def _option(name: str, diet: str, *items: str) -> dict:
    return {"name": name, "diet": diet, "items": list(items)}


# Each session has options across diet styles; the generator rotates them across the week.
MEAL_OPTIONS: dict[str, list[dict]] = {
    "Breakfast": [
        _option("Oats & berry bowl", "vegan", "Rolled oats", "Soy milk", "Mixed berries", "Chia seeds"),
        _option("Chia pudding", "vegan", "Chia seeds", "Soy milk", "Mixed berries", "Almonds"),
        _option("Tofu scramble", "vegan", "Firm tofu", "Whole-wheat bread", "Spinach"),
        _option("PB banana toast", "vegan", "Whole-wheat bread", "Peanut butter", "Banana"),
        _option("Protein oats", "vegetarian", "Rolled oats", "Milk", "Whey protein", "Banana"),
        _option("Yoghurt parfait", "vegetarian", "Greek yoghurt", "Mixed berries", "Almonds"),
        _option("Eggs on toast", "eggetarian", "Eggs", "Whole-wheat bread", "Avocado"),
    ],
    "Lunch": [
        _option("Chickpea quinoa salad", "vegan", "Chickpeas (cooked)", "Quinoa (cooked)", "Salad greens", "Olive oil"),
        _option("Tempeh stir-fry", "vegan", "Tempeh", "Brown rice (cooked)", "Mixed vegetables", "Olive oil"),
        _option("Lentil & veg bowl", "vegan", "Red lentils (cooked)", "Quinoa (cooked)", "Mixed vegetables", "Olive oil"),
        _option("Tofu poke bowl", "vegan", "Firm tofu", "Brown rice (cooked)", "Edamame", "Avocado"),
        _option("Paneer rice bowl", "vegetarian", "Paneer", "Brown rice (cooked)", "Mixed vegetables"),
        _option("Egg salad bowl", "eggetarian", "Eggs", "Quinoa (cooked)", "Salad greens", "Avocado"),
        _option("Chicken & rice bowl", "non_vegetarian", "Chicken breast", "Brown rice (cooked)", "Mixed vegetables", "Olive oil"),
        _option("Tuna pasta", "non_vegetarian", "Tuna", "Whole-wheat pasta (cooked)", "Salad greens", "Olive oil"),
    ],
    "Snack": [
        _option("Nuts & fruit", "vegan", "Mixed nuts", "Apple"),
        _option("PB toast", "vegan", "Peanut butter", "Whole-wheat bread"),
        _option("Edamame & banana", "vegan", "Edamame", "Banana"),
        _option("Plant protein shake", "vegan", "Pea protein", "Soy milk", "Banana"),
        _option("Yoghurt & almonds", "vegetarian", "Greek yoghurt", "Almonds"),
        _option("Cottage cheese bowl", "vegetarian", "Cottage cheese", "Mixed berries"),
    ],
    "Dinner": [
        _option("Lentil dal & rice", "vegan", "Red lentils (cooked)", "Brown rice (cooked)", "Spinach", "Olive oil"),
        _option("Black bean bowl", "vegan", "Black beans (cooked)", "Quinoa (cooked)", "Broccoli", "Avocado"),
        _option("Tofu curry", "vegan", "Firm tofu", "Brown rice (cooked)", "Mixed vegetables", "Olive oil"),
        _option("Chickpea curry", "vegan", "Chickpeas (cooked)", "Quinoa (cooked)", "Spinach", "Olive oil"),
        _option("Salmon & sweet potato", "non_vegetarian", "Salmon fillet", "Sweet potato", "Broccoli"),
        _option("Beef & roast veg", "non_vegetarian", "Lean beef", "Sweet potato", "Mixed vegetables"),
    ],
}

SESSIONS = ["Breakfast", "Lunch", "Snack", "Dinner"]

# Share of the daily calorie target per session.
SESSION_CALORIE_SHARE = {"Breakfast": 0.25, "Lunch": 0.30, "Snack": 0.15, "Dinner": 0.30}

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
