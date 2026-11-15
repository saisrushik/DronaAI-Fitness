import { formatChange, useUnitSystem } from "../lib/units";

export interface WeeklyReview {
  id: string;
  period_start: string;
  period_end: string;
  stats: {
    days_logged: number;
    planned_sessions: number;
    completed_sessions: number;
    workout_adherence: number | null;
    meals_logged: number;
    meals_followed: number;
    meal_adherence: number | null;
    avg_mood: number | null;
    avg_energy: number | null;
    avg_soreness: number | null;
    avg_sleep_hours: number | null;
    start_weight_kg: number | null;
    end_weight_kg: number | null;
    weekly_change_kg: number | null;
    expected_weekly_change_kg: number;
    goal: string;
  };
  summary: string;
  recommended_adjustment: number;
  status: "open" | "applied" | "dismissed" | "superseded" | "none";
  resolved_at: string | null;
  created_at: string;
}

const STATUS: Record<WeeklyReview["status"], { label: string; style: string }> = {
  open: { label: "Adjustment suggested", style: "bg-amber-100 text-amber-800" },
  applied: { label: "Adjustment applied", style: "bg-emerald-100 text-emerald-800" },
  dismissed: { label: "Kept current target", style: "bg-slate-100 text-slate-700" },
  superseded: { label: "Replaced by a newer review", style: "bg-slate-100 text-slate-500" },
  none: { label: "No change needed", style: "bg-indigo-50 text-indigo-700" },
};

const shortDate = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short" });

const kcal = (value: number) => `${value > 0 ? "+" : ""}${value} kcal/day`;

function Chip({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 px-3 py-2">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="font-semibold text-slate-900">{value}</dd>
    </div>
  );
}

interface Props {
  reviews: WeeklyReview[];
  /** Coaches act on suggestions; customers only see them. */
  onApply?: (review: WeeklyReview) => void;
  onDismiss?: (review: WeeklyReview) => void;
  busyId?: string | null;
  emptyText: string;
}

/** Weekly plan reviews (FR-5.6) with their calorie suggestion (FR-5.7). */
export default function WeeklyReviewList({ reviews, onApply, onDismiss, busyId, emptyText }: Props) {
  const system = useUnitSystem();

  if (reviews.length === 0) {
    return <p className="text-sm text-slate-500">{emptyText}</p>;
  }

  return (
    <ul className="space-y-4">
      {reviews.map((review) => {
        const { stats } = review;
        const status = STATUS[review.status];
        const busy = busyId === review.id;
        return (
          <li key={review.id} className="rounded-xl border border-slate-200 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="font-semibold text-slate-900">
                {shortDate(review.period_start)} – {shortDate(review.period_end)}
              </h3>
              <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${status.style}`}>
                {status.label}
                {review.recommended_adjustment !== 0 && ` · ${kcal(review.recommended_adjustment)}`}
              </span>
            </div>

            <dl className="mt-3 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
              <Chip label="Days logged" value={`${stats.days_logged} / 7`} />
              <Chip
                label="Workouts"
                value={stats.workout_adherence === null ? "—" : `${stats.workout_adherence}%`}
              />
              <Chip
                label="Meals on plan"
                value={stats.meal_adherence === null ? "—" : `${stats.meal_adherence}%`}
              />
              <Chip
                label="Weight / week"
                value={
                  stats.weekly_change_kg === null
                    ? "—"
                    : `${formatChange(stats.weekly_change_kg, system)} (aim ${formatChange(
                        stats.expected_weekly_change_kg,
                        system,
                      )})`
                }
              />
            </dl>
            {(stats.avg_mood !== null || stats.avg_energy !== null || stats.avg_sleep_hours !== null) && (
              <p className="mt-2 text-xs text-slate-500">
                {[
                  stats.avg_mood !== null && `Mood ${stats.avg_mood}/5`,
                  stats.avg_energy !== null && `Energy ${stats.avg_energy}/5`,
                  stats.avg_soreness !== null && `Soreness ${stats.avg_soreness}/5`,
                  stats.avg_sleep_hours !== null && `Sleep ${stats.avg_sleep_hours} h`,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            )}

            <p className="mt-3 text-sm text-slate-700">{review.summary}</p>

            {review.status === "open" &&
              (onApply && onDismiss ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="btn-primary btn-sm"
                    disabled={busy}
                    onClick={() => onApply(review)}
                  >
                    {busy ? "Saving…" : `Apply ${kcal(review.recommended_adjustment)}`}
                  </button>
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    disabled={busy}
                    onClick={() => onDismiss(review)}
                  >
                    Keep current target
                  </button>
                </div>
              ) : (
                <p className="mt-3 text-xs text-slate-500">
                  Your coach will decide whether to apply this change.
                </p>
              ))}
          </li>
        );
      })}
    </ul>
  );
}
