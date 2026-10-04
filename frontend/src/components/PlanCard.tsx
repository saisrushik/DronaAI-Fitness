import type { ReactNode } from "react";
import { formatDateTime } from "../lib/requests";
import WeeklyDietPlan, {
  type ManageMeal,
  type MealEditing,
  type WeeklyDietContent,
} from "./WeeklyDietPlan";

export interface WorkoutContent {
  goal: string;
  days_per_week: number;
  days: {
    day: string;
    focus: string;
    exercises: { name: string; sets: number; reps: string }[];
    removed_for_safety: string[];
  }[];
  notes: string;
}

export interface Plan {
  id: string;
  plan_type: "workout" | "diet";
  title: string;
  content: WorkoutContent | WeeklyDietContent | null;
  approved_at: string | null;
  created_at: string;
}

/** Customer-only: ticks off this week's planned exercises. */
export interface WorkoutTracking {
  /** Weekday name -> "YYYY-MM-DD" in the current week. */
  dates: Record<string, string>;
  today: string;
  isDone: (date: string, exercise: string) => boolean;
  onToggle: (date: string, exercise: string, done: boolean) => void;
  /** "date|exercise" currently being saved. */
  saving: string | null;
}

const shortDay = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
  });

function CheckMark() {
  return (
    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={3} aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 12.5l4.5 4.5L19 7.5" />
    </svg>
  );
}

function WorkoutView({ content, tracking }: { content: WorkoutContent; tracking?: WorkoutTracking }) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {content.days.map((day) => {
        const date = tracking?.dates[day.day];
        const upcoming = !!date && !!tracking && date > tracking.today;
        const doneCount =
          date && tracking ? day.exercises.filter((e) => tracking.isDone(date, e.name)).length : 0;
        const complete = doneCount > 0 && doneCount === day.exercises.length;

        return (
          <div
            key={day.day}
            className={`rounded-xl border p-4 ${complete ? "border-emerald-300 bg-emerald-50/40" : "border-slate-200"}`}
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h4 className="font-semibold">{day.day}</h4>
                {date && <p className="text-xs text-slate-500">{shortDay(date)}</p>}
              </div>
              <div className="flex flex-wrap items-center gap-1.5">
                {tracking && date && !upcoming && (
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                      complete
                        ? "bg-emerald-100 text-emerald-800"
                        : doneCount
                          ? "bg-amber-100 text-amber-800"
                          : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {doneCount}/{day.exercises.length} done
                  </span>
                )}
                <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
                  {day.focus}
                </span>
              </div>
            </div>
            <ul className="mt-3 divide-y divide-slate-100">
              {day.exercises.map((exercise) => {
                const done = !!date && !!tracking?.isDone(date, exercise.name);
                const busy = tracking?.saving === `${date}|${exercise.name}`;
                return (
                  <li key={exercise.name} className="flex items-center justify-between gap-3 py-2 text-sm">
                    {tracking && date ? (
                      <button
                        type="button"
                        role="checkbox"
                        aria-checked={done}
                        disabled={upcoming || busy}
                        onClick={() => tracking.onToggle(date, exercise.name, !done)}
                        title={upcoming ? `You can tick this off on ${shortDay(date)}` : undefined}
                        className="group flex min-w-0 items-center gap-2.5 text-left disabled:cursor-not-allowed"
                      >
                        <span
                          className={`grid h-5 w-5 shrink-0 place-items-center rounded-md border-2 transition ${
                            done
                              ? "border-emerald-600 bg-emerald-600 text-white"
                              : upcoming
                                ? "border-slate-200 bg-slate-50"
                                : "border-slate-300 bg-white group-hover:border-emerald-500"
                          } ${busy ? "animate-pulse" : ""}`}
                        >
                          {done && <CheckMark />}
                        </span>
                        <span
                          className={`min-w-0 ${done ? "text-slate-500 line-through" : upcoming ? "text-slate-400" : "text-slate-700"}`}
                        >
                          {exercise.name}
                        </span>
                      </button>
                    ) : (
                      <span className="min-w-0 text-slate-700">{exercise.name}</span>
                    )}
                    <span className="shrink-0 whitespace-nowrap text-slate-500">
                      {exercise.sets} × {exercise.reps}
                    </span>
                  </li>
                );
              })}
            </ul>
            {day.removed_for_safety.length > 0 && (
              <p className="mt-2 text-xs text-amber-600">
                Removed for safety: {day.removed_for_safety.join(", ")}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

interface PlanCardProps {
  plan: Plan;
  dietEdit?: MealEditing;
  onManageMeal?: ManageMeal;
  workoutTracking?: WorkoutTracking;
  headerAction?: ReactNode;
  /** Rendered between the header and the plan itself. */
  children?: ReactNode;
}

export default function PlanCard({
  plan,
  dietEdit,
  onManageMeal,
  headerAction,
  children,
  workoutTracking,
}: PlanCardProps) {
  const isWorkout = plan.plan_type === "workout";

  if (!plan.content) {
    return (
      <article className="card">
        <h3 className="text-lg font-semibold">{plan.title}</h3>
        <p className="mt-2 text-sm text-slate-500">
          Waiting for the customer to approve this plan.
        </p>
      </article>
    );
  }

  return (
    <article className="card">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-lg font-semibold">{plan.title}</h3>
          <span className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-slate-500">
            {!plan.approved_at && (
              <span className="rounded-full bg-amber-100 px-2 py-0.5 font-medium text-amber-800">
                Awaiting approval
              </span>
            )}
            {isWorkout ? "Workout" : "Diet"} · {formatDateTime(plan.created_at)}
          </span>
        </div>
        {headerAction}
      </div>

      {children}

      <div className="mt-4">
        {isWorkout ? (
          <WorkoutView content={plan.content as WorkoutContent} tracking={workoutTracking} />
        ) : (
          <WeeklyDietPlan
            content={plan.content as WeeklyDietContent}
            edit={dietEdit}
            onManageMeal={onManageMeal}
          />
        )}
      </div>

      <p className="mt-4 text-sm text-slate-500">{plan.content.notes}</p>
    </article>
  );
}
