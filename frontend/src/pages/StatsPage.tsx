import { useEffect } from "react";
import { Link } from "react-router-dom";
import HealthMetricsPanel from "../components/HealthMetricsPanel";
import UnitToggle from "../components/UnitToggle";
import { useAuth, type User } from "../context/AuthContext";
import { api } from "../lib/api";
import { labelFor } from "../lib/profileOptions";
import {
  formatChange,
  formatHeight,
  formatLength,
  formatWeight,
  useUnitSystem,
} from "../lib/units";

function Measure({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-slate-50 p-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-0.5 font-semibold text-slate-900">{value}</p>
    </div>
  );
}

function BreakdownRow({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className={`flex justify-between gap-4 py-2 text-sm ${strong ? "font-semibold text-slate-900" : "text-slate-700"}`}>
      <dt>{label}</dt>
      <dd className="tabular-nums">{value}</dd>
    </div>
  );
}

const kcal = (value: number, sign = false) =>
  `${sign && value > 0 ? "+" : ""}${value < 0 ? "−" : ""}${Math.abs(value)} kcal`;

/** BRD FR-2.11: every calculator result in one place. */
export default function StatsPage() {
  const { user, setUser } = useAuth();
  const system = useUnitSystem();

  // Pick up changes made since login, such as a coach applying a weekly calorie adjustment.
  useEffect(() => {
    api
      .get<User>("/auth/me")
      .then(setUser)
      .catch(() => undefined);
  }, [setUser]);

  if (user?.role !== "customer") {
    return <p className="py-20 text-center text-slate-500">This page is for customers.</p>;
  }

  const c = user.customer;
  const metrics = user.metrics;
  const breakdown = metrics?.calorie_breakdown;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold sm:text-3xl">My stats</h1>
          <p className="mt-1 text-slate-600">
            All your health calculations in one place. Hover over (or tap){" "}
            <span className="inline-grid h-4 w-4 place-items-center rounded-full border border-slate-300 bg-white text-[10px] font-bold text-slate-500">
              i
            </span>{" "}
            on any result to see how it&apos;s worked out.
          </p>
        </div>
        <UnitToggle />
      </header>

      {!metrics || !c || !breakdown ? (
        <div className="card text-center">
          <h2 className="font-semibold">Your stats aren&apos;t ready yet</h2>
          <p className="mt-2 text-sm text-slate-600">
            Finish your profile so we can calculate your BMI, calories, macros and more.
          </p>
          <Link to="/profile" className="btn-primary mx-auto mt-4">
            Complete my profile
          </Link>
        </div>
      ) : (
        <>
          <div className="grid gap-6 lg:grid-cols-3">
            <section className="card lg:col-span-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-lg font-semibold">Current measurements</h2>
                <div className="flex gap-2">
                  <Link to="/profile#log-measurements" className="btn-soft btn-sm">
                    Log measurements
                  </Link>
                  <Link to="/monitoring" className="btn-secondary btn-sm">
                    Trends
                  </Link>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
                <Measure label="Weight" value={formatWeight(c.weight_kg, system)} />
                <Measure label="Height" value={formatHeight(c.height_cm, system)} />
                <Measure label="Age" value={c.age !== null ? `${c.age} years` : "—"} />
                <Measure label="Waist" value={formatLength(c.waist_cm, system)} />
                <Measure label="Neck" value={formatLength(c.neck_cm, system)} />
                <Measure label="Hip" value={formatLength(c.hip_cm, system)} />
              </div>
            </section>

            <section className="card">
              <h2 className="text-lg font-semibold">Daily calorie target</h2>
              <dl className="mt-3 divide-y divide-slate-100">
                <BreakdownRow label="Maintenance (TDEE)" value={kcal(breakdown.tdee)} />
                <BreakdownRow
                  label={`Goal: ${labelFor("goal", c.primary_goal)}`}
                  value={kcal(breakdown.goal_delta, true)}
                />
                {breakdown.coach_adjustment !== 0 && (
                  <BreakdownRow
                    label="Coach adjustment"
                    value={kcal(breakdown.coach_adjustment, true)}
                  />
                )}
                <BreakdownRow label="Daily target" value={kcal(breakdown.target)} strong />
              </dl>
              {metrics.calorie_floor_applied && (
                <p className="mt-2 text-xs text-amber-700">
                  Raised to the {breakdown.floor} kcal safety floor.
                </p>
              )}
              <p className="mt-3 text-xs text-slate-500">
                {breakdown.expected_weekly_change_kg === 0
                  ? "Your goal aims to keep your weight about the same."
                  : `Your goal aims for about ${formatChange(
                      breakdown.expected_weekly_change_kg,
                      system,
                    )} a week. Weekly reviews on your Progress page check how you're tracking.`}
              </p>
            </section>
          </div>

          <section className="card">
            <h2 className="text-lg font-semibold">Health metrics</h2>
            <div className="mt-4">
              <HealthMetricsPanel metrics={metrics} />
            </div>
          </section>
        </>
      )}
    </div>
  );
}
