import type { WeeklyDietContent } from "../components/WeeklyDietPlan";
import type { WorkoutContent } from "../components/PlanCard";

export type MealStatus = "followed" | "other" | "skipped";

export type ActivityType = "walk" | "run" | "calisthenics" | "other";

export interface Activity {
  type: ActivityType;
  name: string;
  amount: number;
  unit: string;
}

// Mirrors the API's presets; "other" lets the customer name the activity and unit.
export const ACTIVITY_TYPES: { type: ActivityType; label: string; unit: string; max: number; step: string }[] = [
  { type: "walk", label: "Brisk walk", unit: "steps", max: 100_000, step: "1" },
  { type: "run", label: "Running", unit: "km", max: 200, step: "0.1" },
  { type: "calisthenics", label: "Calisthenics", unit: "hours", max: 24, step: "0.25" },
  { type: "other", label: "Other", unit: "", max: 100_000, step: "any" },
];

export interface ProgressLog {
  log_date: string;
  workout: {
    completed: boolean;
    plan_day: string | null;
    exercises: { name: string; done: boolean }[];
    activities?: Activity[];
  } | null;
  meals: { session: string; status: MealStatus; note: string }[] | null;
  mood: number | null;
  energy: number | null;
  soreness: number | null;
  sleep_hours: number | null;
  notes: string;
  updated_at: string;
}

export const DEFAULT_SESSIONS = ["Breakfast", "Lunch", "Snack", "Dinner"];

/** "YYYY-MM-DD" for a local calendar day. */
export function isoDay(date: Date): string {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

export const fromIsoDay = (day: string) => new Date(`${day}T00:00:00`);

export const weekdayOf = (day: string) =>
  fromIsoDay(day).toLocaleDateString("en-US", { weekday: "long" });

export function shiftDay(day: string, offset: number): string {
  const date = fromIsoDay(day);
  date.setDate(date.getDate() + offset);
  return isoDay(date);
}

export const lastDays = (count: number, today = isoDay(new Date())) =>
  Array.from({ length: count }, (_, i) => shiftDay(today, i - count + 1));

/** Weekday name -> date ("YYYY-MM-DD") for the Monday-to-Sunday week containing today. */
export function currentWeek(today = isoDay(new Date())): Record<string, string> {
  const offsetFromMonday = (fromIsoDay(today).getDay() + 6) % 7;
  const monday = shiftDay(today, -offsetFromMonday);
  const week: Record<string, string> = {};
  for (let i = 0; i < 7; i += 1) {
    const day = shiftDay(monday, i);
    week[weekdayOf(day)] = day;
  }
  return week;
}

/** Done when every planned exercise is ticked; partial when only some work was logged. */
export function workoutStatus(log: ProgressLog | undefined): "done" | "partial" | null {
  if (!log?.workout) return null;
  return log.workout.completed ? "done" : "partial";
}

export function workoutDayFor(plan: WorkoutContent | null, day: string) {
  return plan?.days.find((d) => d.day === weekdayOf(day)) ?? null;
}

export function mealSessionsFor(plan: WeeklyDietContent | null, day: string): string[] {
  const planned = plan?.days.find((d) => d.day === weekdayOf(day));
  return planned ? planned.sessions.map((s) => s.name) : DEFAULT_SESSIONS;
}

/** Consecutive logged days ending today, or yesterday if today isn't logged yet. */
export function currentStreak(logged: Set<string>, today = isoDay(new Date())): number {
  let day = logged.has(today) ? today : shiftDay(today, -1);
  let streak = 0;
  while (logged.has(day)) {
    streak += 1;
    day = shiftDay(day, -1);
  }
  return streak;
}
