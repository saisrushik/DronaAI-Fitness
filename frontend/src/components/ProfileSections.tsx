import type { ReactNode } from "react";
import type { CustomerProfile } from "../context/AuthContext";
import {
  activityLevels,
  blankInjury,
  bodyParts,
  budgetLevels,
  dietTypes,
  goals,
  injurySeverities,
  medicalConditions,
  recoveryStatuses,
  stressLevels,
  TRAINING_DAYS,
  trainingExperience,
  trainingLocations,
  type Injury,
  type Option,
} from "../lib/profileOptions";
import { unitLabel, useUnitSystem } from "../lib/units";
import { HeightInput, MeasureInput } from "./UnitInputs";

const MAX_INJURIES = 20;

/** Form state for the customer profile. Numbers stay strings while being typed. */
export interface ProfileDraft {
  height_cm: string;
  weight_kg: string;
  waist_cm: string;
  neck_cm: string;
  hip_cm: string;
  activity_level: string;
  primary_goal: string;
  diet_type: string;
  budget_level: string;
  dietary_preferences: string;
  medical_conditions: string[];
  stress_level: string;
  injuries: Injury[];
  training_experience: string;
  training_location: string;
  training_days_per_week: number;
}

export type UpdateDraft = <K extends keyof ProfileDraft>(field: K, value: ProfileDraft[K]) => void;

interface SectionProps {
  draft: ProfileDraft;
  update: UpdateDraft;
}

const text = (value: number | null | undefined) => (value == null ? "" : String(value));

export function draftFromProfile(profile: CustomerProfile | null | undefined): ProfileDraft {
  return {
    height_cm: text(profile?.height_cm),
    weight_kg: text(profile?.weight_kg),
    waist_cm: text(profile?.waist_cm),
    neck_cm: text(profile?.neck_cm),
    hip_cm: text(profile?.hip_cm),
    activity_level: profile?.activity_level ?? "moderate",
    primary_goal: profile?.primary_goal ?? "general_fitness",
    diet_type: profile?.diet_type ?? "vegetarian",
    budget_level: profile?.budget_level ?? "medium",
    dietary_preferences: profile?.dietary_preferences?.join(", ") ?? "",
    medical_conditions: profile?.medical_conditions ?? [],
    stress_level: profile?.stress_level ?? "medium",
    injuries: profile?.injuries ?? [],
    training_experience: profile?.training_experience ?? "beginner",
    training_location: profile?.training_location ?? "gym",
    training_days_per_week: profile?.training_days_per_week ?? 3,
  };
}

/** Turns "vegan, no dairy" into ["vegan", "no dairy"]. */
export function toList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

const optionalNumber = (value: string) => (value ? Number(value) : null);

export function payloadFromDraft(draft: ProfileDraft) {
  return {
    height_cm: Number(draft.height_cm),
    weight_kg: Number(draft.weight_kg),
    waist_cm: optionalNumber(draft.waist_cm),
    neck_cm: optionalNumber(draft.neck_cm),
    hip_cm: optionalNumber(draft.hip_cm),
    activity_level: draft.activity_level,
    primary_goal: draft.primary_goal,
    diet_type: draft.diet_type,
    budget_level: draft.budget_level,
    dietary_preferences: toList(draft.dietary_preferences),
    medical_conditions: draft.medical_conditions,
    stress_level: draft.stress_level,
    injuries: draft.injuries.map((injury) => ({
      ...injury,
      date_of_injury: injury.date_of_injury || null,
      notes: injury.notes.trim(),
    })),
    training_experience: draft.training_experience,
    training_location: draft.training_location,
    training_days_per_week: draft.training_days_per_week,
  };
}

/** Radio-style cards for picking one option. */
export function ChoiceCards({
  name,
  options,
  value,
  onChange,
  columns = "sm:grid-cols-2",
}: {
  name: string;
  options: Option[];
  value: string;
  onChange: (value: string) => void;
  columns?: string;
}) {
  return (
    <div role="radiogroup" aria-label={name} className={`grid gap-2 ${columns}`}>
      {options.map((option) => {
        const selected = value === option.value;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(option.value)}
            className={`rounded-xl border p-3 text-left transition ${
              selected ? "border-indigo-500 bg-indigo-50" : "border-slate-300 hover:bg-slate-50"
            }`}
          >
            <span className="block font-medium text-slate-900">{option.label}</span>
            {option.description && (
              <span className="mt-1 block text-xs text-slate-600">{option.description}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}

function Field({
  label,
  htmlFor,
  hint,
  children,
}: {
  label: string;
  htmlFor?: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div>
      {htmlFor ? (
        <label className="label" htmlFor={htmlFor}>
          {label}
        </label>
      ) : (
        <span className="label">{label}</span>
      )}
      {children}
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

export function BodySection({ draft, update }: SectionProps) {
  const system = useUnitSystem();
  const length = unitLabel("length", system);
  const circumference = (
    field: "waist_cm" | "neck_cm" | "hip_cm",
    id: string,
    label: string,
    min: number,
    max: number,
    placeholder: string,
  ) => (
    <Field label={`${label} (${length})`} htmlFor={id}>
      <MeasureInput
        id={id}
        quantity="length"
        system={system}
        value={draft[field]}
        onChange={(v) => update(field, v)}
        min={min}
        max={max}
        placeholder={placeholder}
      />
    </Field>
  );

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={system === "imperial" ? "Height (ft, in)" : "Height (cm)"} htmlFor="height">
          <HeightInput
            id="height"
            system={system}
            value={draft.height_cm}
            onChange={(v) => update("height_cm", v)}
            required
            placeholder="175"
          />
        </Field>
        <Field label={`Weight (${unitLabel("weight", system)})`} htmlFor="weight">
          <MeasureInput
            id="weight"
            quantity="weight"
            system={system}
            value={draft.weight_kg}
            onChange={(v) => update("weight_kg", v)}
            min={30}
            max={250}
            required
            placeholder={system === "imperial" ? "160" : "72"}
          />
        </Field>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        {circumference("waist_cm", "waist", "Waist", 40, 200, system === "imperial" ? "36" : "92")}
        {circumference("neck_cm", "neck", "Neck", 20, 60, system === "imperial" ? "15" : "39")}
        {circumference("hip_cm", "hip", "Hip", 40, 200, system === "imperial" ? "38" : "96")}
      </div>
      <p className="text-xs text-slate-500">
        Waist and neck power your body fat estimate; hip is only used for women. Measure the
        waist at the navel, the neck just below the Adam&apos;s apple and the hips at their widest
        point.
      </p>
    </div>
  );
}

export function ActivitySection({ draft, update }: SectionProps) {
  return (
    <ChoiceCards
      name="Activity level"
      options={activityLevels}
      value={draft.activity_level}
      onChange={(v) => update("activity_level", v)}
    />
  );
}

export function GoalSection({ draft, update }: SectionProps) {
  return (
    <ChoiceCards
      name="Primary goal"
      options={goals}
      value={draft.primary_goal}
      onChange={(v) => update("primary_goal", v)}
    />
  );
}

export function DietSection({ draft, update }: SectionProps) {
  return (
    <div className="space-y-5">
      <Field label="Diet type">
        <ChoiceCards
          name="Diet type"
          options={dietTypes}
          value={draft.diet_type}
          onChange={(v) => update("diet_type", v)}
        />
      </Field>
      <Field label="Food budget" hint="Helps your coach pick ingredients you can buy regularly.">
        <ChoiceCards
          name="Food budget"
          options={budgetLevels}
          value={draft.budget_level}
          onChange={(v) => update("budget_level", v)}
          columns="sm:grid-cols-3"
        />
      </Field>
      <Field label="Allergies & restrictions" htmlFor="restrictions" hint="Separate with commas.">
        <input
          id="restrictions"
          value={draft.dietary_preferences}
          onChange={(e) => update("dietary_preferences", e.target.value)}
          className="input"
          placeholder="no dairy, peanut allergy, gluten free"
        />
      </Field>
    </div>
  );
}

type InjurySelectField = "body_part" | "severity" | "recovery_status";

function InjuryRow({
  injury,
  index,
  onChange,
  onRemove,
}: {
  injury: Injury;
  index: number;
  onChange: (injury: Injury) => void;
  onRemove: () => void;
}) {
  const set = <K extends keyof Injury>(field: K, value: Injury[K]) =>
    onChange({ ...injury, [field]: value });
  const id = (field: string) => `injury-${index}-${field}`;
  const select = (field: InjurySelectField, label: string, options: Option[]) => (
    <Field label={label} htmlFor={id(field)}>
      <select
        id={id(field)}
        value={injury[field]}
        onChange={(e) => set(field, e.target.value)}
        className="input"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </Field>
  );

  return (
    <li className="rounded-xl border border-slate-200 p-3">
      <div className="grid gap-3 sm:grid-cols-3">
        {select("body_part", "Body part", bodyParts)}
        {select("severity", "Severity", injurySeverities)}
        {select("recovery_status", "Status", recoveryStatuses)}
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-[10rem_1fr]">
        <Field label="Date (optional)" htmlFor={id("date")}>
          <input
            id={id("date")}
            type="date"
            max={new Date().toISOString().slice(0, 10)}
            value={injury.date_of_injury ?? ""}
            onChange={(e) => set("date_of_injury", e.target.value || null)}
            className="input"
          />
        </Field>
        <Field label="Notes (optional)" htmlFor={id("notes")}>
          <input
            id={id("notes")}
            maxLength={200}
            value={injury.notes}
            onChange={(e) => set("notes", e.target.value)}
            className="input"
            placeholder="e.g. ACL surgery, hurts on stairs"
          />
        </Field>
      </div>
      <button
        type="button"
        onClick={onRemove}
        className="mt-3 text-xs font-medium text-red-600 hover:underline"
      >
        Remove injury
      </button>
    </li>
  );
}

export function HealthSection({ draft, update }: SectionProps) {
  const toggleCondition = (value: string) =>
    update(
      "medical_conditions",
      draft.medical_conditions.includes(value)
        ? draft.medical_conditions.filter((c) => c !== value)
        : [...draft.medical_conditions, value],
    );
  const setInjury = (index: number, injury: Injury) =>
    update(
      "injuries",
      draft.injuries.map((existing, i) => (i === index ? injury : existing)),
    );

  return (
    <div className="space-y-6">
      <Field label="Medical conditions" hint="Select any that apply.">
        <div className="grid gap-2 sm:grid-cols-2">
          {medicalConditions.map((condition) => (
            <label
              key={condition.value}
              className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm"
            >
              <input
                type="checkbox"
                checked={draft.medical_conditions.includes(condition.value)}
                onChange={() => toggleCondition(condition.value)}
                className="h-4 w-4 rounded border-slate-300"
              />
              {condition.label}
            </label>
          ))}
        </div>
        {draft.medical_conditions.length > 0 && (
          <p className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            Your plans are general fitness guidance, not medical advice. With a medical condition,
            check any plan with your doctor before you start, and stop if you feel unwell.
          </p>
        )}
      </Field>

      <Field
        label="Stress level"
        hint="High stress slows recovery, so your training volume is reduced."
      >
        <ChoiceCards
          name="Stress level"
          options={stressLevels}
          value={draft.stress_level}
          onChange={(v) => update("stress_level", v)}
          columns="sm:grid-cols-3"
        />
      </Field>

      <Field
        label="Injuries"
        hint="Exercises that load an injured area are left out of your workout plan."
      >
        {draft.injuries.length === 0 ? (
          <p className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-500">
            No injuries added.
          </p>
        ) : (
          <ul className="space-y-3">
            {draft.injuries.map((injury, index) => (
              <InjuryRow
                key={index}
                index={index}
                injury={injury}
                onChange={(next) => setInjury(index, next)}
                onRemove={() =>
                  update(
                    "injuries",
                    draft.injuries.filter((_, i) => i !== index),
                  )
                }
              />
            ))}
          </ul>
        )}
        <button
          type="button"
          className="btn-soft btn-sm mt-3"
          disabled={draft.injuries.length >= MAX_INJURIES}
          onClick={() => update("injuries", [...draft.injuries, blankInjury()])}
        >
          + Add injury
        </button>
      </Field>
    </div>
  );
}

export function TrainingSection({ draft, update }: SectionProps) {
  return (
    <div className="space-y-5">
      <Field label="Training experience">
        <ChoiceCards
          name="Training experience"
          options={trainingExperience}
          value={draft.training_experience}
          onChange={(v) => update("training_experience", v)}
          columns="sm:grid-cols-3"
        />
      </Field>
      <Field label="Where do you train?">
        <ChoiceCards
          name="Training location"
          options={trainingLocations}
          value={draft.training_location}
          onChange={(v) => update("training_location", v)}
        />
      </Field>
      <Field label="Training days per week">
        <div role="radiogroup" aria-label="Training days per week" className="flex flex-wrap gap-2">
          {TRAINING_DAYS.map((days) => (
            <button
              key={days}
              type="button"
              role="radio"
              aria-checked={draft.training_days_per_week === days}
              onClick={() => update("training_days_per_week", days)}
              className={`h-11 w-11 rounded-xl border text-sm font-semibold transition ${
                draft.training_days_per_week === days
                  ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                  : "border-slate-300 text-slate-700 hover:bg-slate-50"
              }`}
            >
              {days}
            </button>
          ))}
        </div>
      </Field>
    </div>
  );
}
