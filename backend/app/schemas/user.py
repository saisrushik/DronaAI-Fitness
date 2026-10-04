import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.core.security import validate_password

Role = Literal["customer", "coach"]
Gender = Literal["male", "female", "other"]
ActivityLevel = Literal["sedentary", "light", "moderate", "active", "very_active"]
Goal = Literal["lose_fat", "build_muscle", "maintain", "improve_endurance"]
DietType = Literal["vegetarian", "non_vegetarian", "eggetarian", "vegan"]
PlanType = Literal["workout", "diet"]

MIN_AGE = 18
MAX_AGE = 70

# Emails are stored lowercase so the same address can't register twice with different casing.
Email = Annotated[EmailStr, AfterValidator(str.lower)]
ProfileNote = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


def age_from(date_of_birth: date) -> int:
    today = date.today()
    had_birthday = (today.month, today.day) >= (date_of_birth.month, date_of_birth.day)
    return today.year - date_of_birth.year - (0 if had_birthday else 1)


# --- Auth ---
class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(default="", max_length=60)
    email: Email
    password: str = Field(max_length=128)
    role: Role = "customer"
    accepted_disclaimer: bool = False

    # Customers supply their measurements at sign-up; coaches leave these empty.
    date_of_birth: date | None = None
    gender: Gender | None = None
    height_cm: float | None = Field(default=None, ge=100, le=250)
    weight_kg: float | None = Field(default=None, ge=30, le=250)
    waist_cm: float | None = Field(default=None, ge=40, le=200)
    neck_cm: float | None = Field(default=None, ge=20, le=60)
    hip_cm: float | None = Field(default=None, ge=40, le=200)

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        return validate_password(value)

    @model_validator(mode="after")
    def check_customer_fields(self) -> "RegisterRequest":
        if not self.accepted_disclaimer:
            raise ValueError("You must accept the medical disclaimer to create an account")

        if self.role == "customer":
            missing = [
                name
                for name in (
                    "date_of_birth",
                    "gender",
                    "height_cm",
                    "weight_kg",
                    "waist_cm",
                    "neck_cm",
                )
                if getattr(self, name) is None
            ]
            if missing:
                raise ValueError(f"Customers must provide: {', '.join(missing)}")

            age = age_from(self.date_of_birth)
            if not MIN_AGE <= age <= MAX_AGE:
                raise ValueError(
                    f"DronaAI.fit is only available to people aged {MIN_AGE}-{MAX_AGE}."
                )
        return self


class LoginRequest(BaseModel):
    email: Email
    password: str = Field(max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str


# --- Profiles ---
class CustomerProfileUpdate(BaseModel):
    height_cm: float = Field(ge=100, le=250)
    weight_kg: float = Field(ge=30, le=250)
    waist_cm: float | None = Field(default=None, ge=40, le=200)
    neck_cm: float | None = Field(default=None, ge=20, le=60)
    hip_cm: float | None = Field(default=None, ge=40, le=200)
    activity_level: ActivityLevel
    primary_goal: Goal
    diet_type: DietType
    dietary_preferences: list[ProfileNote] = Field(default=[], max_length=20)
    health_injury_history: list[ProfileNote] = Field(default=[], max_length=20)


class CoachProfileUpdate(BaseModel):
    specialization: str = Field(min_length=1, max_length=120)
    years_experience: int = Field(ge=0, le=60)
    bio: str = Field(default="", max_length=500)


class AccountUpdate(BaseModel):
    """Name, email, role and demographics. Email and role changes need the current password."""

    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(default="", max_length=60)
    email: Email
    role: Role
    gender: Gender | None = None
    date_of_birth: date | None = None
    current_password: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def check_age(self) -> "AccountUpdate":
        self.first_name = self.first_name.strip()
        self.last_name = self.last_name.strip()
        if not self.first_name:
            raise ValueError("First name can't be empty")
        if self.date_of_birth is not None:
            age = age_from(self.date_of_birth)
            if not MIN_AGE <= age <= MAX_AGE:
                raise ValueError(
                    f"DronaAI.fit is only available to people aged {MIN_AGE}-{MAX_AGE}."
                )
        return self


# --- Body measurement log ---
class MeasurementCreate(BaseModel):
    """Any subset of measurements; at least one is required."""

    weight_kg: float | None = Field(default=None, ge=30, le=250)
    height_cm: float | None = Field(default=None, ge=100, le=250)
    waist_cm: float | None = Field(default=None, ge=40, le=200)
    neck_cm: float | None = Field(default=None, ge=20, le=60)
    hip_cm: float | None = Field(default=None, ge=40, le=200)
    recorded_at: datetime | None = None

    @model_validator(mode="after")
    def check_values(self) -> "MeasurementCreate":
        if all(
            getattr(self, f) is None
            for f in ("weight_kg", "height_cm", "waist_cm", "neck_cm", "hip_cm")
        ):
            raise ValueError("Enter at least one measurement")
        if self.recorded_at is not None:
            if self.recorded_at.tzinfo is None:
                self.recorded_at = self.recorded_at.replace(tzinfo=timezone.utc)
            if self.recorded_at > datetime.now(timezone.utc) + timedelta(minutes=5):
                raise ValueError("Measurements can't be logged in the future")
            if self.recorded_at.year < 2000:
                raise ValueError("Enter a date after the year 2000")
        return self


class MeasurementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recorded_at: datetime
    weight_kg: float | None
    height_cm: float | None
    waist_cm: float | None
    neck_cm: float | None
    hip_cm: float | None


# --- Daily progress tracking ---
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]

# type -> (name, unit, maximum amount); "other" activities name their own unit.
ACTIVITY_PRESETS = {
    "walk": ("Brisk walk", "steps", 100_000),
    "run": ("Running", "km", 200),
    "calisthenics": ("Calisthenics", "hours", 24),
}


class Activity(BaseModel):
    """Exercise done outside the plan, measured in a unit that suits it."""

    type: Literal["walk", "run", "calisthenics", "other"]
    name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] = ""
    amount: float = Field(gt=0, le=100_000)
    unit: Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)] = ""

    @model_validator(mode="after")
    def apply_preset(self) -> "Activity":
        preset = ACTIVITY_PRESETS.get(self.type)
        if preset:
            self.name, self.unit, limit = preset
            if self.amount > limit:
                raise ValueError(f"{self.name} can be at most {limit} {self.unit}")
        elif not self.name or not self.unit:
            raise ValueError("Give other activities a name and a unit, e.g. Swimming in laps")
        return self


class ExerciseToggle(BaseModel):
    """Marks one exercise from the customer's workout plan as done or not done."""

    name: str = Field(min_length=1, max_length=80)
    done: bool


class MealLog(BaseModel):
    session: str = Field(min_length=1, max_length=40)
    status: Literal["followed", "other", "skipped"]
    note: ShortText = ""


Scale = Annotated[int, Field(ge=1, le=5)]


class ProgressLogUpsert(BaseModel):
    """The daily check-in. Plan exercises are ticked off separately, from the workout plan."""

    activities: list[Activity] = Field(default=[], max_length=20)
    meals: list[MealLog] = Field(default=[], max_length=10)
    mood: Scale | None = None
    energy: Scale | None = None
    soreness: Scale | None = None
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    notes: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def check_unique_meals(self) -> "ProgressLogUpsert":
        sessions = [meal.session for meal in self.meals]
        if len(sessions) != len(set(sessions)):
            raise ValueError("Each meal can only be logged once per day")
        return self


class ProgressLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    log_date: date
    workout: dict | None
    meals: list[dict] | None
    mood: int | None
    energy: int | None
    soreness: int | None
    sleep_hours: float | None
    notes: str
    updated_at: datetime


class CustomerProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    coach_id: uuid.UUID | None
    share_code: str
    date_of_birth: date | None
    age: int | None
    gender: str | None
    height_cm: float | None
    weight_kg: float | None
    waist_cm: float | None
    neck_cm: float | None
    hip_cm: float | None
    activity_level: str | None
    primary_goal: str | None
    diet_type: str | None
    dietary_preferences: list[str] | None
    health_injury_history: list[str] | None
    profile_completed: bool


class CoachProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    specialization: str | None
    years_experience: int | None
    bio: str | None
    gender: str | None
    date_of_birth: date | None
    profile_completed: bool


class MeResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    full_name: str
    role: Role
    profile_completed: bool
    customer: CustomerProfile | None = None
    coach: CoachProfile | None = None
    metrics: dict | None = None


# --- Plans ---
class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    coach_id: uuid.UUID
    plan_type: PlanType
    title: str
    content: dict | None
    approved_at: datetime | None
    created_at: datetime


class GeneratePlanRequest(BaseModel):
    plan_type: PlanType


class LinkCustomerRequest(BaseModel):
    share_code: str = Field(min_length=4, max_length=12)


# --- Customer requests ---
RequestType = Literal["meal", "workout", "injury", "query"]
RequestStatus = Literal["pending", "approved", "rejected", "resolved"]
FoodName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
MAX_ITEMS_PER_MEAL = 12
MAX_MEALS_PER_REQUEST = 28  # every meal of the week


class _MealRef(BaseModel):
    day: str = Field(min_length=1, max_length=20)
    session: str = Field(min_length=1, max_length=40)


def _unique_meals(meals: list[_MealRef]) -> None:
    keys = [(m.day, m.session) for m in meals]
    if len(keys) != len(set(keys)):
        raise ValueError("Each meal can only appear once per request")


class RequestedMeal(_MealRef):
    items: list[FoodName] = Field(min_length=1, max_length=MAX_ITEMS_PER_MEAL)


class MealRequestCreate(BaseModel):
    plan_id: uuid.UUID
    meals: list[RequestedMeal] = Field(min_length=1, max_length=MAX_MEALS_PER_REQUEST)
    description: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def check_unique(self) -> "MealRequestCreate":
        _unique_meals(self.meals)
        return self


class CustomerRequestCreate(BaseModel):
    """Workout changes, injuries and questions. Meal requests come from the diet plan page."""

    request_type: Literal["workout", "injury", "query"]
    description: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=5, max_length=1000)
    ]


class ApprovedItem(BaseModel):
    name: FoodName
    quantity: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
    calories: float = Field(ge=0, le=5000)
    protein_g: float = Field(ge=0, le=500)
    carbs_g: float = Field(ge=0, le=500)
    fat_g: float = Field(ge=0, le=500)


class ApprovedMeal(_MealRef):
    """Nutrition for the foods the customer added; foods they kept retain their values."""

    items: list[ApprovedItem] = Field(default=[], max_length=MAX_ITEMS_PER_MEAL)


class MealUpdate(_MealRef):
    """A coach replacing every food in one meal of a diet plan."""

    items: list[ApprovedItem] = Field(min_length=1, max_length=MAX_ITEMS_PER_MEAL)


class DietChangeApproval(BaseModel):
    meals: list[ApprovedMeal] = Field(min_length=1, max_length=MAX_MEALS_PER_REQUEST)
    note: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def check_unique(self) -> "DietChangeApproval":
        _unique_meals(self.meals)
        return self


class CoachResponse(BaseModel):
    note: str = Field(default="", max_length=500)


class CustomerRequestResponse(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    customer_name: str
    plan_id: uuid.UUID | None
    plan_title: str | None
    request_type: RequestType
    status: RequestStatus
    description: str
    requested_meals: list[dict] | None
    approved_meals: list[dict] | None
    coach_note: str
    created_at: datetime
    resolved_at: datetime | None


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    request_id: uuid.UUID | None
    message: str
    read_at: datetime | None
    created_at: datetime


class NotificationList(BaseModel):
    unread: int
    items: list[NotificationResponse]


# --- Coach dashboard ---
class CustomerSummary(BaseModel):
    id: uuid.UUID
    full_name: str
    email: EmailStr
    profile_completed: bool
    date_of_birth: date | None
    age: int | None
    gender: str | None
    height_cm: float | None
    weight_kg: float | None
    waist_cm: float | None
    neck_cm: float | None
    hip_cm: float | None
    activity_level: str | None
    primary_goal: str | None
    diet_type: str | None
    dietary_preferences: list[str] | None
    health_injury_history: list[str] | None
    bmi: float | None
    workout_plan_count: int
    diet_plan_count: int
    pending_requests: int


class CustomerDetail(CustomerSummary):
    metrics: dict | None
    plans: list[PlanResponse]
