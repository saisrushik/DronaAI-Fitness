import WeeklyDietPlan, { type WeeklyDietContent } from "./WeeklyDietPlan";

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

function WorkoutView({ content }: { content: WorkoutContent }) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {content.days.map((day) => (
        <div key={day.day} className="rounded-xl border border-slate-200 p-4">
          <div className="flex items-baseline justify-between">
            <h4 className="font-semibold">{day.day}</h4>
            <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
              {day.focus}
            </span>
          </div>
          <ul className="mt-3 divide-y divide-slate-100">
            {day.exercises.map((exercise) => (
              <li key={exercise.name} className="flex justify-between py-2 text-sm">
                <span className="text-slate-700">{exercise.name}</span>
                <span className="text-slate-500">
                  {exercise.sets} × {exercise.reps}
                </span>
              </li>
            ))}
          </ul>
          {day.removed_for_safety.length > 0 && (
            <p className="mt-2 text-xs text-amber-600">
              Removed for safety: {day.removed_for_safety.join(", ")}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

export default function PlanCard({ plan }: { plan: Plan }) {
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
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-lg font-semibold">{plan.title}</h3>
        <span className="flex items-center gap-2 text-xs text-slate-500">
          {!plan.approved_at && (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 font-medium text-amber-800">
              Awaiting approval
            </span>
          )}
          {isWorkout ? "Workout" : "Diet"} · {new Date(plan.created_at).toLocaleDateString()}
        </span>
      </div>

      <div className="mt-4">
        {isWorkout ? (
          <WorkoutView content={plan.content as WorkoutContent} />
        ) : (
          <WeeklyDietPlan content={plan.content as WeeklyDietContent} />
        )}
      </div>

      <p className="mt-4 text-sm text-slate-500">{plan.content.notes}</p>
    </article>
  );
}
