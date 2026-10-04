import { useEffect, useState } from "react";
import EditableDietPlan from "./EditableDietPlan";
import PlanCard, { type Plan, type WorkoutTracking } from "./PlanCard";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import { currentWeek, isoDay, type ProgressLog } from "../lib/progress";
import type { CustomerRequest } from "../lib/requests";

interface Props {
  planType: "workout" | "diet";
  title: string;
  subtitle: string;
}

function ApprovalCard({ plan, onApprove }: { plan: Plan; onApprove: (id: string) => void }) {
  const [busy, setBusy] = useState(false);

  const approve = async () => {
    setBusy(true);
    await onApprove(plan.id);
    setBusy(false);
  };

  return (
    <article className="card border-amber-200 bg-amber-50">
      <h2 className="text-lg font-semibold text-amber-900">Your coach created a new plan</h2>
      <p className="mt-1 text-sm text-amber-900">
        <span className="font-medium">{plan.title}</span> ·{" "}
        {new Date(plan.created_at).toLocaleDateString()}
      </p>

      <p className="mt-4 text-xs leading-relaxed text-amber-800">
        This plan is general fitness and nutrition guidance, not medical advice. Check with a
        healthcare professional before starting it, especially if you have a medical condition or
        are recovering from an injury. Stop and seek help if you feel unwell.
      </p>

      <button onClick={approve} className="btn-primary mt-4 w-full sm:w-auto" disabled={busy}>
        {busy ? "Approving…" : "I understand — show me the plan"}
      </button>
    </article>
  );
}

/** Shared view for the customer's Workout Plan and Diet Plan pages. */
export default function MyPlanView({ planType, title, subtitle }: Props) {
  const { user } = useAuth();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [requests, setRequests] = useState<CustomerRequest[]>([]);
  const [logs, setLogs] = useState<Record<string, ProgressLog>>({});
  const [saving, setSaving] = useState<string | null>(null);
  const [trackError, setTrackError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = () =>
    Promise.all([
      api.get<Plan[]>("/plans/mine"),
      planType === "diet" ? api.get<CustomerRequest[]>("/requests") : Promise.resolve([]),
      planType === "workout" ? api.get<ProgressLog[]>("/progress?days=8") : Promise.resolve([]),
    ])
      .then(([allPlans, myRequests, progress]) => {
        setPlans(allPlans.filter((p) => p.plan_type === planType));
        setRequests(myRequests);
        setLogs(Object.fromEntries(progress.map((log) => [log.log_date, log])));
      })
      .finally(() => setLoading(false));

  useEffect(() => {
    void load();
  }, [planType]);

  const approve = async (id: string) => {
    await api.post(`/plans/${id}/approve`);
    await load();
  };

  if (loading) return <p className="py-20 text-center text-slate-500">Loading…</p>;

  const pending = plans.filter((p) => !p.approved_at);
  const approved = plans.filter((p) => p.approved_at);

  const today = isoDay(new Date());
  const tracking: WorkoutTracking = {
    dates: currentWeek(today),
    today,
    isDone: (date, name) =>
      !!logs[date]?.workout?.exercises.some((e) => e.name === name && e.done),
    saving,
    onToggle: async (date, name, done) => {
      setTrackError("");
      setSaving(`${date}|${name}`);
      try {
        const log = await api.post<ProgressLog>(`/progress/${date}/exercises`, { name, done });
        setLogs((prev) => ({ ...prev, [date]: log }));
      } catch (err) {
        setTrackError(err instanceof Error ? err.message : "Could not update your progress");
      } finally {
        setSaving(null);
      }
    },
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold sm:text-3xl">{title}</h1>
        <p className="mt-1 text-slate-600">{subtitle}</p>
      </header>

      {pending.map((plan) => (
        <ApprovalCard key={plan.id} plan={plan} onApprove={approve} />
      ))}

      {approved.length === 0 && pending.length === 0 ? (
        <p className="card text-slate-500">
          No {planType} plan yet. Only your coach can generate plans for you.
        </p>
      ) : (
        approved.map((plan) =>
          planType === "diet" ? (
            <EditableDietPlan
              key={plan.id}
              plan={plan}
              requests={requests.filter(
                (r) => r.request_type === "meal" && r.plan_id === plan.id,
              )}
              hasCoach={!!user?.customer?.coach_id}
              onChanged={load}
            />
          ) : (
            // Ticks count against the newest accepted plan, so only that one is tickable.
            <PlanCard
              key={plan.id}
              plan={plan}
              workoutTracking={plan.id === approved[0].id ? tracking : undefined}
            >
              {plan.id === approved[0].id && (
                <p className="mt-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
                  Tick off exercises as you finish them this week — they show up in your
                  progress tracking automatically.
                  {trackError && <span className="mt-1 block text-red-600">{trackError}</span>}
                </p>
              )}
            </PlanCard>
          ),
        )
      )}
    </div>
  );
}
