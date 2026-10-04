import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import LineChart from "../components/LineChart";
import type { Plan, WorkoutContent } from "../components/PlanCard";
import type { WeeklyDietContent } from "../components/WeeklyDietPlan";
import { useAuth, type User } from "../context/AuthContext";
import { api } from "../lib/api";
import type { Measurement } from "../lib/measurements";
import {
  ACTIVITY_TYPES,
  currentStreak,
  fromIsoDay,
  isoDay,
  lastDays,
  mealSessionsFor,
  shiftDay,
  workoutDayFor,
  workoutStatus,
  type ActivityType,
  type MealStatus,
  type ProgressLog,
} from "../lib/progress";

const MEAL_OPTIONS: { value: MealStatus; label: string; active: string }[] = [
  { value: "followed", label: "Followed plan", active: "border-emerald-500 bg-emerald-50 text-emerald-800" },
  { value: "other", label: "Ate something else", active: "border-amber-500 bg-amber-50 text-amber-800" },
  { value: "skipped", label: "Skipped", active: "border-slate-500 bg-slate-100 text-slate-800" },
];

const SCALES = [
  { key: "mood", label: "Mood", low: "Low", high: "Great" },
  { key: "energy", label: "Energy", low: "Drained", high: "Energised" },
  { key: "soreness", label: "Soreness", low: "None", high: "Very sore" },
] as const;

type ScaleKey = (typeof SCALES)[number]["key"];

interface ActivityDraft {
  type: ActivityType;
  name: string;
  amount: string;
  unit: string;
}

interface CheckIn {
  activities: ActivityDraft[];
  meals: Record<string, { status: MealStatus | null; note: string }>;
  mood: number | null;
  energy: number | null;
  soreness: number | null;
  sleep_hours: string;
  notes: string;
  weight: string;
}

const prettyDay = (day: string) =>
  fromIsoDay(day).toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" });

const toNumber = (text: string) => (text.trim() === "" ? null : Number(text));

const activityConfig = (type: ActivityType) => ACTIVITY_TYPES.find((a) => a.type === type)!;

function buildCheckIn(
  day: string,
  log: ProgressLog | undefined,
  dietPlan: WeeklyDietContent | null,
): CheckIn {
  const meals: CheckIn["meals"] = {};
  for (const session of mealSessionsFor(dietPlan, day)) {
    const logged = log?.meals?.find((m) => m.session === session);
    meals[session] = { status: logged?.status ?? null, note: logged?.note ?? "" };
  }

  return {
    activities: (log?.workout?.activities ?? []).map((a) => ({
      type: a.type,
      name: a.type === "other" ? a.name : "",
      amount: String(a.amount),
      unit: a.type === "other" ? a.unit : "",
    })),
    meals,
    mood: log?.mood ?? null,
    energy: log?.energy ?? null,
    soreness: log?.soreness ?? null,
    sleep_hours: log?.sleep_hours?.toString() ?? "",
    notes: log?.notes ?? "",
    weight: "",
  };
}

function StatTile({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-slate-900">{value}</p>
      <p className="mt-0.5 text-xs text-slate-500">{hint}</p>
    </div>
  );
}

export default function ProgressPage() {
  const { user, setUser } = useAuth();
  const today = isoDay(new Date());
  const [logs, setLogs] = useState<ProgressLog[]>([]);
  const [weights, setWeights] = useState<Measurement[]>([]);
  const [workoutPlan, setWorkoutPlan] = useState<WorkoutContent | null>(null);
  const [dietPlan, setDietPlan] = useState<WeeklyDietContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [day, setDay] = useState(today);
  const [form, setForm] = useState<CheckIn | null>(null);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(
    () =>
      Promise.all([
        api.get<ProgressLog[]>("/progress?days=90"),
        api.get<Measurement[]>("/measurements"),
        api.get<Plan[]>("/plans/mine"),
      ]).then(([progress, measurements, plans]) => {
        setLogs(progress);
        setWeights(measurements);
        // Plans come newest first; use the latest one the customer has accepted.
        const latest = (type: Plan["plan_type"]) =>
          plans.find((p) => p.plan_type === type && p.approved_at && p.content)?.content ?? null;
        setWorkoutPlan(latest("workout") as WorkoutContent | null);
        setDietPlan(latest("diet") as WeeklyDietContent | null);
      }),
    [],
  );

  useEffect(() => {
    if (user?.role !== "customer") return;
    load()
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load your progress"))
      .finally(() => setLoading(false));
  }, [load, user?.role]);

  const byDay = useMemo(() => new Map(logs.map((log) => [log.log_date, log])), [logs]);

  useEffect(() => {
    if (loading) return;
    setForm(buildCheckIn(day, byDay.get(day), dietPlan));
  }, [day, loading, byDay, dietPlan]);

  useEffect(() => {
    setStatus("");
    setError("");
  }, [day]);

  const stats = useMemo(() => {
    const week = lastDays(7, today);
    const planned = week.filter((d) => workoutDayFor(workoutPlan, d));
    const trained = planned.filter((d) => byDay.get(d)?.workout?.completed);
    const meals = week.flatMap((d) => byDay.get(d)?.meals ?? []);
    const followed = meals.filter((m) => m.status === "followed");
    const sleeps = week
      .map((d) => byDay.get(d)?.sleep_hours)
      .filter((h): h is number => h !== null && h !== undefined);
    return {
      streak: currentStreak(new Set(byDay.keys()), today),
      workout: planned.length ? Math.round((trained.length / planned.length) * 100) : null,
      workoutHint: `${trained.length} of ${planned.length} planned sessions this week`,
      meals: meals.length ? Math.round((followed.length / meals.length) * 100) : null,
      mealsHint: `${followed.length} of ${meals.length} logged meals on plan`,
      sleep: sleeps.length ? sleeps.reduce((a, b) => a + b, 0) / sleeps.length : null,
    };
  }, [byDay, workoutPlan, today]);

  if (user?.role !== "customer") {
    return <p className="py-20 text-center text-slate-500">This page is for customers.</p>;
  }
  if (loading || !form) {
    return <p className="py-20 text-center text-slate-500">Loading your progress…</p>;
  }

  const plannedDay = workoutDayFor(workoutPlan, day);
  const doneOnPlan = new Set(
    (byDay.get(day)?.workout?.exercises ?? []).filter((e) => e.done).map((e) => e.name),
  );
  const update = (patch: Partial<CheckIn>) => setForm((prev) => (prev ? { ...prev, ...patch } : prev));
  const setActivity = (index: number, patch: Partial<ActivityDraft>) =>
    update({ activities: form.activities.map((a, i) => (i === index ? { ...a, ...patch } : a)) });
  const setMeal = (session: string, patch: Partial<CheckIn["meals"][string]>) =>
    update({ meals: { ...form.meals, [session]: { ...form.meals[session], ...patch } } });

  const save = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    setStatus("");
    try {
      await api.put(`/progress/${day}`, {
        activities: form.activities
          .filter((a) => a.amount.trim())
          .map((a) => ({
            type: a.type,
            name: a.type === "other" ? a.name.trim() : "",
            amount: Number(a.amount),
            unit: a.type === "other" ? a.unit.trim() : "",
          })),
        meals: Object.entries(form.meals)
          .filter(([, meal]) => meal.status)
          .map(([session, meal]) => ({
            session,
            status: meal.status,
            note: meal.status === "other" ? meal.note : "",
          })),
        mood: form.mood,
        energy: form.energy,
        soreness: form.soreness,
        sleep_hours: toNumber(form.sleep_hours),
        notes: form.notes,
      });
      if (form.weight.trim()) {
        const recordedAt = day === today ? new Date() : new Date(`${day}T08:00:00`);
        await api.post("/measurements", {
          weight_kg: Number(form.weight),
          recorded_at: recordedAt.toISOString(),
        });
        setUser(await api.get<User>("/auth/me"));
      }
      await load();
      setStatus(`Saved your check-in for ${prettyDay(day)}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save your check-in");
    } finally {
      setSaving(false);
    }
  };

  const weightSeries = {
    key: "weight",
    label: "Weight",
    unit: "kg",
    color: "#6366f1",
    points: weights
      .filter((m) => m.weight_kg !== null)
      .map((m) => ({ t: Date.parse(m.recorded_at), v: m.weight_kg as number })),
  };
  const wellness = (
    [
      ["mood", "Mood", "#10b981"],
      ["energy", "Energy", "#f59e0b"],
      ["soreness", "Soreness", "#f43f5e"],
    ] as const
  ).map(([key, label, color]) => ({
    key,
    label,
    unit: "/ 5",
    color,
    points: logs
      .filter((log) => log[key] !== null)
      .map((log) => ({ t: fromIsoDay(log.log_date).getTime(), v: log[key] as number })),
  }));
  const recent = lastDays(14, today).reverse();

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold sm:text-3xl">Progress tracking</h1>
          <p className="mt-1 text-slate-600">
            Check in each day with your workout, meals and how you feel.
          </p>
        </div>
        <Link to="/monitoring" className="btn-soft w-full sm:w-auto">
          Body measurement trends
        </Link>
      </header>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          label="Streak"
          value={`${stats.streak} day${stats.streak === 1 ? "" : "s"}`}
          hint="Consecutive days checked in"
        />
        <StatTile
          label="Workout adherence"
          value={stats.workout === null ? "—" : `${stats.workout}%`}
          hint={workoutPlan ? stats.workoutHint : "No accepted workout plan yet"}
        />
        <StatTile
          label="Meal adherence"
          value={stats.meals === null ? "—" : `${stats.meals}%`}
          hint={stats.mealsHint}
        />
        <StatTile
          label="Average sleep"
          value={stats.sleep === null ? "—" : `${stats.sleep.toFixed(1)} h`}
          hint="Over the last 7 days"
        />
      </div>

      <form onSubmit={save} className="card space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-semibold">Daily check-in</h2>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="btn-secondary px-3"
              onClick={() => setDay(shiftDay(day, -1))}
              aria-label="Previous day"
            >
              ‹
            </button>
            <input
              type="date"
              value={day}
              max={today}
              onChange={(e) => e.target.value && setDay(e.target.value)}
              className="input w-auto"
              aria-label="Check-in date"
            />
            <button
              type="button"
              className="btn-secondary px-3"
              onClick={() => setDay(shiftDay(day, 1))}
              disabled={day >= today}
              aria-label="Next day"
            >
              ›
            </button>
          </div>
        </div>

        <section className="space-y-3">
          <div>
            <h3 className="font-semibold text-slate-900">Workout</h3>
            <p className="text-sm text-slate-500">
              {plannedDay
                ? `Planned for ${plannedDay.day}: ${plannedDay.focus}`
                : workoutPlan
                  ? "Rest day in your plan — log anything you did anyway."
                  : "You don't have an accepted workout plan yet."}
            </p>
          </div>

          {plannedDay && (
            <div className="rounded-lg bg-slate-50 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-medium text-slate-700">
                  From your plan · {doneOnPlan.size}/{plannedDay.exercises.length} done
                </p>
                <Link to="/workout-plan" className="btn-soft btn-sm">
                  Tick off on workout plan
                </Link>
              </div>
              <ul className="mt-2 grid gap-1.5 sm:grid-cols-2">
                {plannedDay.exercises.map((exercise) => {
                  const done = doneOnPlan.has(exercise.name);
                  return (
                    <li key={exercise.name} className="flex items-center gap-2 text-sm">
                      <span
                        className={`grid h-5 w-5 shrink-0 place-items-center rounded-md border-2 ${
                          done ? "border-emerald-600 bg-emerald-600 text-white" : "border-slate-300 bg-white"
                        }`}
                        aria-hidden
                      >
                        {done && (
                          <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={3}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 12.5l4.5 4.5L19 7.5" />
                          </svg>
                        )}
                      </span>
                      <span className={done ? "text-slate-800" : "text-slate-500"}>
                        {exercise.name}
                        <span className="sr-only">{done ? " (done)" : " (not done)"}</span>
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          <div className="space-y-2">
            <p className="text-sm font-medium text-slate-700">Other exercise</p>
            {form.activities.map((activity, index) => {
              const config = activityConfig(activity.type);
              const isOther = activity.type === "other";
              return (
                <div
                  key={index}
                  className={`grid gap-2 rounded-lg bg-slate-50 p-3 sm:items-center ${
                    isOther
                      ? "sm:grid-cols-[11rem_minmax(0,1fr)_7rem_7rem_auto]"
                      : "sm:grid-cols-[11rem_minmax(0,1fr)_auto]"
                  }`}
                >
                  <select
                    className="input bg-white"
                    aria-label="Exercise type"
                    value={activity.type}
                    onChange={(e) => setActivity(index, { type: e.target.value as ActivityType })}
                  >
                    {ACTIVITY_TYPES.map((option) => (
                      <option key={option.type} value={option.type}>
                        {option.label}
                        {option.unit ? ` (${option.unit})` : ""}
                      </option>
                    ))}
                  </select>
                  {isOther && (
                    <input
                      className="input bg-white"
                      maxLength={80}
                      required
                      placeholder="Exercise, e.g. Swimming"
                      aria-label="Exercise name"
                      value={activity.name}
                      onChange={(e) => setActivity(index, { name: e.target.value })}
                    />
                  )}
                  <div className="relative">
                    <input
                      className={`input bg-white ${isOther ? "" : "pr-16"}`}
                      type="number"
                      inputMode="decimal"
                      min={0}
                      max={config.max}
                      step={config.step}
                      required
                      placeholder={isOther ? "Amount" : `How many ${config.unit}?`}
                      aria-label={isOther ? "Amount" : `${config.label} in ${config.unit}`}
                      value={activity.amount}
                      onChange={(e) => setActivity(index, { amount: e.target.value })}
                    />
                    {!isOther && (
                      <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-slate-500">
                        {config.unit}
                      </span>
                    )}
                  </div>
                  {isOther && (
                    <input
                      className="input bg-white"
                      maxLength={20}
                      required
                      placeholder="Unit, e.g. laps"
                      aria-label="Unit"
                      value={activity.unit}
                      onChange={(e) => setActivity(index, { unit: e.target.value })}
                    />
                  )}
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    onClick={() => update({ activities: form.activities.filter((_, i) => i !== index) })}
                  >
                    Remove
                  </button>
                </div>
              );
            })}
            <button
              type="button"
              className="btn-soft btn-sm"
              disabled={form.activities.length >= 20}
              onClick={() =>
                update({
                  activities: [...form.activities, { type: "walk", name: "", amount: "", unit: "" }],
                })
              }
            >
              + Add exercise
            </button>
          </div>
        </section>

        <section className="space-y-3 border-t border-slate-100 pt-5">
          <div>
            <h3 className="font-semibold text-slate-900">Meals</h3>
            <p className="text-sm text-slate-500">
              {dietPlan ? "Compared with your diet plan for this day." : "No accepted diet plan yet."}
            </p>
          </div>
          {Object.entries(form.meals).map(([session, meal]) => (
            <div key={session} className="rounded-lg bg-slate-50 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium text-slate-800">{session}</span>
                <div className="flex flex-wrap gap-1.5" role="group" aria-label={`${session} status`}>
                  {MEAL_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      aria-pressed={meal.status === option.value}
                      onClick={() =>
                        setMeal(session, { status: meal.status === option.value ? null : option.value })
                      }
                      className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
                        meal.status === option.value
                          ? option.active
                          : "border-slate-300 bg-white text-slate-600 hover:bg-slate-100"
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>
              {meal.status === "other" && (
                <input
                  className="input mt-2 bg-white"
                  maxLength={200}
                  placeholder="What did you eat?"
                  aria-label={`What you ate for ${session}`}
                  value={meal.note}
                  onChange={(e) => setMeal(session, { note: e.target.value })}
                />
              )}
            </div>
          ))}
        </section>

        <section className="space-y-4 border-t border-slate-100 pt-5">
          <h3 className="font-semibold text-slate-900">How you feel</h3>
          <div className="max-w-xl space-y-4">
            {SCALES.map((scale) => (
              <div
                key={scale.key}
                className="grid gap-1.5 sm:grid-cols-[6rem_minmax(0,1fr)] sm:items-start sm:gap-4"
              >
                <span className="label sm:mb-0 sm:pt-2.5">{scale.label}</span>
                <div>
                  <div className="flex gap-1.5" role="group" aria-label={scale.label}>
                    {[1, 2, 3, 4, 5].map((n) => (
                      <button
                        key={n}
                        type="button"
                        aria-pressed={form[scale.key as ScaleKey] === n}
                        onClick={() =>
                          update({ [scale.key]: form[scale.key as ScaleKey] === n ? null : n })
                        }
                        className={`h-10 flex-1 rounded-lg border text-sm font-semibold transition ${
                          form[scale.key as ScaleKey] === n
                            ? "border-indigo-500 bg-indigo-600 text-white"
                            : "border-slate-300 text-slate-600 hover:bg-slate-50"
                        }`}
                      >
                        {n}
                      </button>
                    ))}
                  </div>
                  <div className="mt-1 flex justify-between text-[11px] text-slate-400">
                    <span>{scale.low}</span>
                    <span>{scale.high}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="grid gap-4 sm:grid-cols-[10rem_10rem_minmax(0,1fr)]">
            <div>
              <label className="label" htmlFor="sleep">
                Sleep (hours)
              </label>
              <input
                id="sleep"
                type="number"
                inputMode="decimal"
                min={0}
                max={24}
                step="0.5"
                value={form.sleep_hours}
                onChange={(e) => update({ sleep_hours: e.target.value })}
                className="input"
              />
            </div>
            <div>
              <label className="label" htmlFor="day-weight">
                Weight (kg)
              </label>
              <input
                id="day-weight"
                type="number"
                inputMode="decimal"
                min={30}
                max={250}
                step="0.1"
                placeholder="Optional"
                value={form.weight}
                onChange={(e) => update({ weight: e.target.value })}
                className="input"
              />
            </div>
            <div>
              <label className="label" htmlFor="day-notes">
                Notes
              </label>
              <input
                id="day-notes"
                maxLength={500}
                value={form.notes}
                onChange={(e) => update({ notes: e.target.value })}
                className="input"
                placeholder="Anything worth remembering about today"
              />
            </div>
          </div>
        </section>

        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex flex-wrap items-center gap-3 border-t border-slate-100 pt-5">
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? "Saving…" : byDay.has(day) ? "Update check-in" : "Save check-in"}
          </button>
          {status && <span className="text-sm text-emerald-600">{status}</span>}
        </div>
      </form>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="card">
          <h2 className="font-semibold">Weight trend</h2>
          <div className="mt-3">
            <LineChart ariaLabel="Weight over time" height={220} series={[weightSeries]} />
          </div>
        </section>
        <section className="card">
          <h2 className="font-semibold">How you&apos;ve felt</h2>
          <div className="mt-3">
            <LineChart ariaLabel="Mood, energy and soreness over time" height={220} series={wellness} />
          </div>
        </section>
      </div>

      <section className="card">
        <h2 className="font-semibold">Last 14 days</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[44rem] text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-4 font-medium">Day</th>
                <th className="py-2 pr-4 font-medium">Workout</th>
                <th className="py-2 pr-4 font-medium">Meals on plan</th>
                <th className="py-2 pr-4 font-medium">Mood</th>
                <th className="py-2 pr-4 font-medium">Energy</th>
                <th className="py-2 pr-4 font-medium">Soreness</th>
                <th className="py-2 pr-4 font-medium">Sleep</th>
                <th className="py-2 font-medium" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {recent.map((d) => {
                const log = byDay.get(d);
                const planned = workoutDayFor(workoutPlan, d);
                const meals = log?.meals ?? [];
                return (
                  <tr key={d} className={d === day ? "bg-indigo-50/60" : ""}>
                    <td className="whitespace-nowrap py-2 pr-4 text-slate-700">{prettyDay(d)}</td>
                    <td className="py-2 pr-4">
                      {workoutStatus(log) === "done" ? (
                        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800">Done</span>
                      ) : workoutStatus(log) === "partial" ? (
                        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">Partial</span>
                      ) : (
                        <span className="text-xs text-slate-400">{planned ? "Not done" : "Rest day"}</span>
                      )}
                    </td>
                    <td className="py-2 pr-4 text-slate-700">
                      {meals.length
                        ? `${meals.filter((m) => m.status === "followed").length} / ${meals.length}`
                        : "—"}
                    </td>
                    {(["mood", "energy", "soreness"] as const).map((key) => (
                      <td key={key} className="py-2 pr-4 text-slate-700">
                        {log?.[key] ? `${log[key]} / 5` : "—"}
                      </td>
                    ))}
                    <td className="py-2 pr-4 text-slate-700">
                      {log?.sleep_hours !== null && log?.sleep_hours !== undefined ? `${log.sleep_hours} h` : "—"}
                    </td>
                    <td className="py-2 text-right">
                      <button
                        type="button"
                        className="btn-soft btn-sm"
                        onClick={() => {
                          setDay(d);
                          window.scrollTo({ top: 0, behavior: "smooth" });
                        }}
                      >
                        {log ? "Edit" : "Log"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
