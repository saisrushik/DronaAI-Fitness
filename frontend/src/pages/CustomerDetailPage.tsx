import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import CoachMealEditor from "../components/CoachMealEditor";
import HealthMetricsPanel from "../components/HealthMetricsPanel";
import PlanCard, { type Plan } from "../components/PlanCard";
import type { DietSession } from "../components/WeeklyDietPlan";
import WeeklyReviewList, { type WeeklyReview } from "../components/WeeklyReviewList";
import type { HealthMetrics } from "../context/AuthContext";
import { api } from "../lib/api";
import { describeInjury, labelFor } from "../lib/profileOptions";
import { formatDateTime } from "../lib/requests";
import { formatHeight, formatLength, formatWeight, useUnitSystem } from "../lib/units";
import type { CustomerSummary } from "./CustomerDashboardPage";

interface CustomerDetail extends CustomerSummary {
  metrics: HealthMetrics | null;
  plans: Plan[];
  reviews: WeeklyReview[];
}

type PlanType = "workout" | "diet";

const time = (iso: string) => new Date(iso).getTime();

/**
 * Plans older than something that changes them: a profile edit (FR-1.8), or, for the diet,
 * a calorie adjustment applied from a weekly review (FR-5.7).
 */
function outdatedPlans(customer: CustomerDetail): { type: PlanType; reasons: string[] }[] {
  const appliedAt = customer.reviews
    .filter((review) => review.status === "applied" && review.resolved_at)
    .map((review) => time(review.resolved_at as string));

  return (["workout", "diet"] as const).flatMap((type) => {
    const latest = customer.plans
      .filter((plan) => plan.plan_type === type)
      .reduce((max, plan) => Math.max(max, time(plan.created_at)), 0);
    if (!latest) return [];
    const reasons: string[] = [];
    if (customer.profile_updated_at && time(customer.profile_updated_at) > latest) {
      reasons.push(`profile updated ${formatDateTime(customer.profile_updated_at)}`);
    }
    if (type === "diet" && appliedAt.some((applied) => applied > latest)) {
      reasons.push("calorie target changed after a weekly review");
    }
    return reasons.length ? [{ type, reasons }] : [];
  });
}

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
  const system = useUnitSystem();
  const [customer, setCustomer] = useState<CustomerDetail | null>(null);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState<"workout" | "diet" | null>(null);
  const [removing, setRemoving] = useState(false);
  const [reviewBusy, setReviewBusy] = useState<string | null>(null);
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

  const generate = async (planType: PlanType) => {
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

  const actOnReview = async (review: WeeklyReview, action: "apply" | "dismiss") => {
    setError("");
    setReviewBusy(review.id);
    try {
      await api.post(`/coach/reviews/${review.id}/${action}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update the review");
    } finally {
      setReviewBusy(null);
    }
  };

  if (error && !customer) return <p className="py-20 text-center text-red-600">{error}</p>;
  if (!customer) return <p className="py-20 text-center text-slate-500">Loading…</p>;

  const outdated = outdatedPlans(customer);

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
      {outdated.length > 0 && (
        <div className="space-y-2 rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-3 text-sm text-indigo-900">
          <p className="font-medium">Some plans are out of date.</p>
          <ul className="space-y-2">
            {outdated.map(({ type, reasons }) => (
              <li key={type} className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <span>
                  <span className="font-semibold capitalize">{type} plan</span>: {reasons.join("; ")}.
                </span>
                <button
                  type="button"
                  className="btn-primary btn-sm shrink-0"
                  onClick={() => generate(type)}
                  disabled={generating !== null}
                >
                  {generating === type ? "Generating…" : `Regenerate ${type} plan`}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-1">
          <div className="card">
            <h2 className="font-semibold">Profile</h2>
            <dl className="mt-2 divide-y divide-slate-100">
              <Row label="Age" value={customer.age?.toString() ?? "—"} />
              <Row label="Gender" value={customer.gender ?? "—"} />
              <Row label="Country" value={labelFor("country", customer.country)} />
              <Row label="Height" value={formatHeight(customer.height_cm, system)} />
              <Row label="Weight" value={formatWeight(customer.weight_kg, system)} />
              <Row label="Waist" value={formatLength(customer.waist_cm, system)} />
              <Row label="Neck" value={formatLength(customer.neck_cm, system)} />
              <Row label="Hip" value={formatLength(customer.hip_cm, system)} />
              <Row label="Activity" value={labelFor("activity", customer.activity_level)} />
              <Row label="Goal" value={labelFor("goal", customer.primary_goal)} />
              <Row label="Diet" value={labelFor("diet", customer.diet_type)} />
              <Row label="Food budget" value={labelFor("budget", customer.budget_level)} />
              <Row label="Restrictions" value={customer.dietary_preferences?.join(", ") || "None"} />
              <Row label="Experience" value={labelFor("experience", customer.training_experience)} />
              <Row label="Trains at" value={labelFor("location", customer.training_location)} />
              <Row
                label="Days per week"
                value={customer.training_days_per_week?.toString() ?? "—"}
              />
            </dl>
          </div>

          <div className="card">
            <h2 className="font-semibold">Health</h2>
            {customer.medical_conditions && customer.medical_conditions.length > 0 && (
              <p className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                <span className="font-semibold">Medical conditions: </span>
                {customer.medical_conditions.map((c) => labelFor("condition", c)).join(", ")}.
                Plans are general guidance; the customer should check them with their doctor.
              </p>
            )}
            <dl className="mt-2 divide-y divide-slate-100">
              {!customer.medical_conditions?.length && <Row label="Conditions" value="None" />}
              <Row label="Stress" value={labelFor("stress", customer.stress_level)} />
            </dl>
            <h3 className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Injuries
            </h3>
            {customer.injuries?.length ? (
              <ul className="mt-2 space-y-2 text-sm">
                {customer.injuries.map((injury, index) => (
                  <li key={index} className="rounded-lg bg-slate-50 px-3 py-2 text-slate-800">
                    {describeInjury(injury)}
                    {injury.date_of_injury && (
                      <span className="block text-xs text-slate-500">
                        Since {new Date(injury.date_of_injury).toLocaleDateString()}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-sm text-slate-500">None</p>
            )}
          </div>
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

      <section className="card">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-xl font-semibold">Weekly reviews</h2>
          <p className="text-sm text-slate-600">
            Calorie adjustment so far:{" "}
            <span className="font-semibold text-slate-900">
              {customer.calorie_adjustment > 0 ? "+" : ""}
              {customer.calorie_adjustment} kcal/day
            </span>
          </p>
        </div>
        <p className="mt-1 text-sm text-slate-600">
          Created automatically after each week of check-ins. Applying a suggestion changes the
          customer&apos;s calorie target; regenerate their diet plan afterwards.
        </p>
        <div className="mt-4">
          <WeeklyReviewList
            reviews={customer.reviews}
            onApply={(review) => actOnReview(review, "apply")}
            onDismiss={(review) => actOnReview(review, "dismiss")}
            busyId={reviewBusy}
            emptyText="No reviews yet. The first one appears after the customer has a week of check-ins (at least 3 days logged)."
          />
        </div>
      </section>

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
