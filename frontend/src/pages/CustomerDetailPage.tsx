import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import CoachMealEditor from "../components/CoachMealEditor";
import HealthMetricsPanel from "../components/HealthMetricsPanel";
import PlanCard, { type Plan } from "../components/PlanCard";
import type { DietSession } from "../components/WeeklyDietPlan";
import type { HealthMetrics } from "../context/AuthContext";
import { api } from "../lib/api";
import type { CustomerSummary } from "./CustomerDashboardPage";

interface CustomerDetail extends CustomerSummary {
  metrics: HealthMetrics | null;
  plans: Plan[];
}

const labels: Record<string, string> = {
  lose_fat: "Lose fat",
  build_muscle: "Build muscle",
  maintain: "Maintain weight",
  improve_endurance: "Improve endurance",
  sedentary: "Sedentary",
  light: "Light",
  moderate: "Moderate",
  active: "Active",
  very_active: "Very active",
  vegetarian: "Vegetarian",
  eggetarian: "Eggetarian",
  non_vegetarian: "Non-vegetarian",
  vegan: "Vegan",
};

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 py-2 text-sm">
      <dt className="shrink-0 text-slate-500">{label}</dt>
      <dd className="min-w-0 break-words text-right font-medium text-slate-800">{value}</dd>
    </div>
  );
}

export default function CustomerDetailPage() {
  const { customerId } = useParams();
  const navigate = useNavigate();
  const [customer, setCustomer] = useState<CustomerDetail | null>(null);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState<"workout" | "diet" | null>(null);
  const [removing, setRemoving] = useState(false);
  const [editingMeal, setEditingMeal] = useState<{
    plan: Plan;
    day: string;
    session: DietSession;
  } | null>(null);

  const load = () =>
    api
      .get<CustomerDetail>(`/coach/customers/${customerId}`)
      .then(setCustomer)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load customer"));

  useEffect(() => {
    void load();
  }, [customerId]);

  const generate = async (planType: "workout" | "diet") => {
    setError("");
    setGenerating(planType);
    try {
      await api.post(`/coach/customers/${customerId}/plans`, { plan_type: planType });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not generate plan");
    } finally {
      setGenerating(null);
    }
  };

  if (error && !customer) return <p className="py-20 text-center text-red-600">{error}</p>;
  if (!customer) return <p className="py-20 text-center text-slate-500">Loading…</p>;

  const remove = async () => {
    const confirmed = window.confirm(
      `Remove ${customer.full_name} from your roster? You'll lose access to their data and ` +
        "any pending requests will be closed. They can share their code with you again later.",
    );
    if (!confirmed) return;
    setError("");
    setRemoving(true);
    try {
      await api.post(`/coach/customers/${customerId}/remove`);
      navigate("/customers", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove this customer");
      setRemoving(false);
    }
  };

  return (
    <div className="space-y-6">
      <Link to="/customers" className="btn-secondary">
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 18l-6-6 6-6" />
        </svg>
        Back to my customers
      </Link>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="break-words text-2xl font-bold sm:text-3xl">{customer.full_name}</h1>
          <p className="mt-1 break-all text-slate-600">{customer.email}</p>
        </div>
        <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
          <button
            onClick={() => generate("workout")}
            className="btn-primary"
            disabled={!customer.profile_completed || generating !== null}
          >
            {generating === "workout" ? "Generating…" : "Generate workout plan"}
          </button>
          <button
            onClick={() => generate("diet")}
            className="btn-secondary"
            disabled={!customer.profile_completed || generating !== null}
          >
            {generating === "diet" ? "Generating…" : "Generate diet plan"}
          </button>
          <button
            onClick={remove}
            className="btn border border-red-200 bg-white text-red-600 hover:bg-red-50"
            disabled={removing}
          >
            {removing ? "Removing…" : "Remove customer"}
          </button>
        </div>
      </header>

      {!customer.profile_completed && (
        <p className="rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-800">
          This customer hasn&apos;t completed their profile yet, so plans can&apos;t be generated.
        </p>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="card lg:col-span-1">
          <h2 className="font-semibold">Profile</h2>
          <dl className="mt-2 divide-y divide-slate-100">
            <Row label="Age" value={customer.age?.toString() ?? "—"} />
            <Row label="Gender" value={customer.gender ?? "—"} />
            <Row label="Height" value={customer.height_cm ? `${customer.height_cm} cm` : "—"} />
            <Row label="Weight" value={customer.weight_kg ? `${customer.weight_kg} kg` : "—"} />
            <Row label="Waist" value={customer.waist_cm ? `${customer.waist_cm} cm` : "—"} />
            <Row label="Neck" value={customer.neck_cm ? `${customer.neck_cm} cm` : "—"} />
            <Row label="Hip" value={customer.hip_cm ? `${customer.hip_cm} cm` : "—"} />
            <Row
              label="Activity"
              value={
                customer.activity_level
                  ? (labels[customer.activity_level] ?? customer.activity_level)
                  : "—"
              }
            />
            <Row
              label="Goal"
              value={
                customer.primary_goal
                  ? (labels[customer.primary_goal] ?? customer.primary_goal)
                  : "—"
              }
            />
            <Row label="Diet" value={customer.diet_type ? (labels[customer.diet_type] ?? customer.diet_type) : "—"} />
            <Row label="Restrictions" value={customer.dietary_preferences?.join(", ") || "None"} />
            <Row label="Injuries" value={customer.health_injury_history?.join(", ") || "None"} />
          </dl>
        </div>

        <div className="card lg:col-span-2">
          <h2 className="font-semibold">Health metrics</h2>
          <div className="mt-4">
            {customer.metrics ? (
              <HealthMetricsPanel metrics={customer.metrics} />
            ) : (
              <p className="text-sm text-slate-500">
                Metrics appear once the customer completes their profile.
              </p>
            )}
          </div>
        </div>
      </div>

      {customer.pending_requests > 0 && (
        <Link
          to="/requests"
          className="flex items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-900 hover:bg-amber-100"
        >
          {customer.full_name} has {customer.pending_requests} pending request
          {customer.pending_requests === 1 ? "" : "s"}
          <span aria-hidden>&rarr;</span>
        </Link>
      )}

      <section className="space-y-4">
        <h2 className="text-xl font-semibold">Plans ({customer.plans.length})</h2>
        {customer.plans.length === 0 ? (
          <p className="card text-slate-500">
            No plans yet. Use the buttons above to generate one.
          </p>
        ) : (
          customer.plans.map((plan) => (
            <PlanCard
              key={plan.id}
              plan={plan}
              onManageMeal={
                plan.plan_type === "diet"
                  ? (day, session) => setEditingMeal({ plan, day, session })
                  : undefined
              }
            />
          ))
        )}
      </section>

      {editingMeal && (
        <CoachMealEditor
          plan={editingMeal.plan}
          day={editingMeal.day}
          session={editingMeal.session}
          onClose={() => setEditingMeal(null)}
          onSaved={load}
        />
      )}
    </div>
  );
}
