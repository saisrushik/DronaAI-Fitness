/** Profile option lists and labels shared by onboarding, the profile form and coach views (BRD 4.1). */

export interface Option {
  value: string;
  label: string;
  description?: string;
}

export const activityLevels: Option[] = [
  { value: "sedentary", label: "Sedentary", description: "Little or no exercise, desk job" },
  { value: "light", label: "Lightly active", description: "Light exercise 1–3 days a week" },
  { value: "moderate", label: "Moderately active", description: "Moderate exercise 3–5 days a week" },
  { value: "active", label: "Very active", description: "Hard exercise 6–7 days a week" },
  {
    value: "very_active",
    label: "Extremely active",
    description: "Physical job or training twice a day",
  },
];

export const goals: Option[] = [
  { value: "lose_fat", label: "Lose fat", description: "Calorie deficit with high protein to keep muscle." },
  { value: "lean_bulk", label: "Lean bulk", description: "Small surplus to gain muscle with minimal fat." },
  {
    value: "aggressive_bulk",
    label: "Aggressive bulk",
    description: "Bigger surplus for maximum muscle; some fat gain expected.",
  },
  { value: "maintain", label: "Maintain", description: "Keep your current weight and shape." },
  {
    value: "recomp",
    label: "Recomposition",
    description: "Lose fat and build muscle at maintenance with very high protein.",
  },
  {
    value: "general_fitness",
    label: "General fitness",
    description: "Balanced training and eating for overall health.",
  },
  { value: "endurance", label: "Endurance", description: "Running and conditioning, fuelled by carbs." },
  { value: "strength", label: "Strength", description: "Heavy, low-rep lifting with a small surplus." },
];

// BRD 4.1.5.
export const dietTypes: Option[] = [
  { value: "vegetarian", label: "Vegetarian", description: "No meat, fish or eggs" },
  { value: "eggetarian", label: "Eggetarian", description: "Vegetarian plus eggs" },
  { value: "non_vegetarian", label: "Non-vegetarian", description: "Includes meat and fish" },
  { value: "vegan", label: "Vegan", description: "No animal products at all" },
];

export const budgetLevels: Option[] = [
  { value: "low", label: "Low", description: "Everyday staples" },
  { value: "medium", label: "Medium", description: "Some premium items" },
  { value: "high", label: "High", description: "Cost isn't a concern" },
];

export const stressLevels: Option[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High", description: "Training volume is reduced to help recovery" },
];

export const medicalConditions: Option[] = [
  { value: "hypertension", label: "High blood pressure" },
  { value: "diabetes", label: "Diabetes" },
  { value: "heart_condition", label: "Heart condition" },
  { value: "pcos", label: "PCOS" },
  { value: "thyroid", label: "Thyroid condition" },
  { value: "asthma", label: "Asthma" },
  { value: "pregnancy", label: "Pregnancy" },
  { value: "other", label: "Other condition" },
];

// BRD 4.1.6.
export const bodyParts: Option[] = [
  { value: "knee", label: "Knee" },
  { value: "lower_back", label: "Lower back" },
  { value: "upper_back", label: "Upper back" },
  { value: "shoulder", label: "Shoulder" },
  { value: "elbow", label: "Elbow" },
  { value: "wrist", label: "Wrist" },
  { value: "hip", label: "Hip" },
  { value: "ankle", label: "Ankle" },
  { value: "neck", label: "Neck" },
  { value: "other", label: "Other" },
];

export const injurySeverities: Option[] = [
  { value: "mild", label: "Mild" },
  { value: "moderate", label: "Moderate" },
  { value: "severe", label: "Severe" },
  { value: "chronic", label: "Chronic" },
];

export const recoveryStatuses: Option[] = [
  { value: "recovered", label: "Recovered" },
  { value: "recovering", label: "Recovering" },
  { value: "active_pain", label: "Still painful" },
];

export const trainingExperience: Option[] = [
  { value: "beginner", label: "Beginner", description: "New to structured training" },
  { value: "intermediate", label: "Intermediate", description: "Training consistently for 6+ months" },
  { value: "advanced", label: "Advanced", description: "Several years of serious training" },
];

export const trainingLocations: Option[] = [
  { value: "gym", label: "Gym", description: "Barbells, machines and dumbbells" },
  { value: "home", label: "Home", description: "Bodyweight and resistance bands" },
];

export const TRAINING_DAYS = [2, 3, 4, 5, 6];

// India first (the MVP market), then alphabetical.
export const countries: Option[] = [
  { value: "IN", label: "India" },
  { value: "AU", label: "Australia" },
  { value: "BD", label: "Bangladesh" },
  { value: "CA", label: "Canada" },
  { value: "DE", label: "Germany" },
  { value: "MX", label: "Mexico" },
  { value: "NP", label: "Nepal" },
  { value: "NZ", label: "New Zealand" },
  { value: "PK", label: "Pakistan" },
  { value: "SA", label: "Saudi Arabia" },
  { value: "SG", label: "Singapore" },
  { value: "LK", label: "Sri Lanka" },
  { value: "AE", label: "United Arab Emirates" },
  { value: "GB", label: "United Kingdom" },
  { value: "US", label: "United States" },
];

// Goals renamed in the BRD update; older plans still carry these keys.
const legacyGoals: Record<string, string> = {
  build_muscle: "Build muscle",
  improve_endurance: "Improve endurance",
};

const lookup = (options: Option[]) =>
  Object.fromEntries(options.map((option) => [option.value, option.label]));

const LABELS: Record<string, Record<string, string>> = {
  activity: lookup(activityLevels),
  goal: { ...lookup(goals), ...legacyGoals },
  diet: lookup(dietTypes),
  budget: lookup(budgetLevels),
  stress: lookup(stressLevels),
  condition: lookup(medicalConditions),
  bodyPart: lookup(bodyParts),
  severity: lookup(injurySeverities),
  recovery: lookup(recoveryStatuses),
  experience: lookup(trainingExperience),
  location: lookup(trainingLocations),
  country: lookup(countries),
};

export type LabelKind = keyof typeof LABELS;

/** Human label for a stored value, falling back to the raw value. */
export function labelFor(kind: LabelKind, value: string | null | undefined, empty = "—"): string {
  if (!value) return empty;
  return LABELS[kind][value] ?? value;
}

export interface Injury {
  body_part: string;
  severity: string;
  recovery_status: string;
  date_of_injury: string | null;
  notes: string;
}

export const blankInjury = (): Injury => ({
  body_part: "knee",
  severity: "mild",
  recovery_status: "recovering",
  date_of_injury: null,
  notes: "",
});

export function describeInjury(injury: Injury): string {
  const parts = [
    labelFor("bodyPart", injury.body_part),
    labelFor("severity", injury.severity).toLowerCase(),
    labelFor("recovery", injury.recovery_status).toLowerCase(),
  ];
  const summary = parts.join(", ");
  return injury.notes ? `${summary} — ${injury.notes}` : summary;
}
