import { useEffect, useState } from "react";
import PlanCard, { type Plan } from "./PlanCard";
import { api } from "../lib/api";

interface CoachInfo {
  full_name: string;
  email: string;
  specialization: string | null;
  years_experience: number | null;
}

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

      <button onClick={approve} className="btn-primary mt-4" disabled={busy}>
        {busy ? "Approving…" : "I understand — show me the plan"}
      </button>
    </article>
  );
}

/** Shared view for the customer's Workout Plan and Diet Plan pages. */
export default function MyPlanView({ planType, title, subtitle }: Props) {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [coach, setCoach] = useState<CoachInfo | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () =>
    Promise.all([api.get<Plan[]>("/plans/mine"), api.get<CoachInfo | null>("/plans/my-coach")])
      .then(([allPlans, myCoach]) => {
        setPlans(allPlans.filter((p) => p.plan_type === planType));
        setCoach(myCoach);
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

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold">{title}</h1>
        <p className="mt-1 text-slate-600">{subtitle}</p>
      </header>

      <div className="card">
        <h2 className="font-semibold">Your coach</h2>
        {coach ? (
          <p className="mt-2 text-sm text-slate-600">
            <span className="font-medium text-slate-900">{coach.full_name}</span>
            {coach.specialization && ` · ${coach.specialization}`}
            {coach.years_experience !== null && ` · ${coach.years_experience} yrs experience`}
          </p>
        ) : (
          <p className="mt-2 text-sm text-slate-500">
            You don&apos;t have a coach yet. Share the code on your profile page with a coach so
            they can start building your plans.
          </p>
        )}
      </div>

      {pending.map((plan) => (
        <ApprovalCard key={plan.id} plan={plan} onApprove={approve} />
      ))}

      {approved.length === 0 && pending.length === 0 ? (
        <p className="card text-slate-500">
          No {planType} plan yet. Only your coach can generate plans for you.
        </p>
      ) : (
        approved.map((plan) => <PlanCard key={plan.id} plan={plan} />)
      )}
    </div>
  );
}
