import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core.security import validate_password

Role = Literal["customer", "coach"]
Gender = Literal["male", "female", "other"]
ActivityLevel = Literal["sedentary", "light", "moderate", "active", "very_active"]
Goal = Literal["lose_fat", "build_muscle", "maintain", "improve_endurance"]
DietType = Literal["vegetarian", "non_vegetarian", "eggetarian", "vegan"]
PlanType = Literal["workout", "diet"]

MIN_AGE = 18
MAX_AGE = 70


def age_from(date_of_birth: date) -> int:
    today = date.today()
    had_birthday = (today.month, today.day) >= (date_of_birth.month, date_of_birth.day)
    return today.year - date_of_birth.year - (0 if had_birthday else 1)


# --- Auth ---
class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(default="", max_length=60)
    email: EmailStr
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
    email: EmailStr
    password: str


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
    dietary_preferences: list[str] = []
    health_injury_history: list[str] = []


class CoachProfileUpdate(BaseModel):
    specialization: str = Field(min_length=1, max_length=120)
    years_experience: int = Field(ge=0, le=60)
    bio: str = Field(default="", max_length=500)


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


class CustomerDetail(CustomerSummary):
    metrics: dict | None
    plans: list[PlanResponse]
