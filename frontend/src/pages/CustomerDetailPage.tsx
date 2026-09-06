import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import HealthMetricsPanel from "../components/HealthMetricsPanel";
import PlanCard, { type Plan } from "../components/PlanCard";
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
      <dt className="text-slate-500">{label}</dt>
      <dd className="text-right font-medium text-slate-800">{value}</dd>
    </div>
  );
}

export default function CustomerDetailPage() {
  const { customerId } = useParams();
  const [customer, setCustomer] = useState<CustomerDetail | null>(null);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState<"workout" | "diet" | null>(null);

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

  return (
    <div className="space-y-6">
      <Link to="/customers" className="text-sm text-indigo-600 hover:underline">
        ← Back to my customers
      </Link>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">{customer.full_name}</h1>
          <p className="mt-1 text-slate-600">{customer.email}</p>
        </div>
        <div className="flex gap-2">
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

      <section className="space-y-4">
        <h2 className="text-xl font-semibold">Plans ({customer.plans.length})</h2>
        {customer.plans.length === 0 ? (
          <p className="card text-slate-500">
            No plans yet. Use the buttons above to generate one.
          </p>
        ) : (
          customer.plans.map((plan) => <PlanCard key={plan.id} plan={plan} />)
        )}
      </section>
    </div>
  );
}
