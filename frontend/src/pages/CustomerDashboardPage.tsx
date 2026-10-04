import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";

export interface CustomerSummary {
  id: string;
  full_name: string;
  email: string;
  profile_completed: boolean;
  date_of_birth: string | null;
  age: number | null;
  gender: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  waist_cm: number | null;
  neck_cm: number | null;
  hip_cm: number | null;
  activity_level: string | null;
  primary_goal: string | null;
  diet_type: string | null;
  dietary_preferences: string[] | null;
  health_injury_history: string[] | null;
  bmi: number | null;
  workout_plan_count: number;
  diet_plan_count: number;
  pending_requests: number;
}

const goalLabels: Record<string, string> = {
  lose_fat: "Lose fat",
  build_muscle: "Build muscle",
  maintain: "Maintain",
  improve_endurance: "Endurance",
};

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl bg-slate-50 p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-slate-900">{value}</p>
    </div>
  );
}

export default function CustomerDashboardPage() {
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [shareCode, setShareCode] = useState("");
  const [error, setError] = useState("");
  const [linkError, setLinkError] = useState("");
  const [linkNotice, setLinkNotice] = useState("");
  const [linking, setLinking] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = () =>
    api
      .get<CustomerSummary[]>("/coach/customers")
      .then(setCustomers)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load customers"))
      .finally(() => setLoading(false));

  useEffect(() => {
    void load();
  }, []);

  const linkCustomer = async (event: FormEvent) => {
    event.preventDefault();
    setLinkError("");
    setLinkNotice("");
    setLinking(true);
    try {
      const added = await api.post<CustomerSummary>("/coach/customers/link", {
        share_code: shareCode.trim().toUpperCase(),
      });
      setLinkNotice(`${added.full_name} added to your roster.`);
      setShareCode("");
      await load();
    } catch (err) {
      setLinkError(err instanceof Error ? err.message : "Could not add customer");
    } finally {
      setLinking(false);
    }
  };

  if (loading) return <p className="py-20 text-center text-slate-500">Loading customers…</p>;

  const totalPlans = customers.reduce(
    (sum, c) => sum + c.workout_plan_count + c.diet_plan_count,
    0,
  );

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-bold sm:text-3xl">My customers</h1>
        <p className="mt-1 text-slate-600">
          Everyone you train, their metrics, and the plans you&apos;ve built for them.
        </p>
      </header>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="grid gap-4 sm:grid-cols-2">
        <Stat label="Customers" value={customers.length} />
        <Stat label="Plans created" value={totalPlans} />
      </div>

      <section className="card">
        <h2 className="text-xl font-semibold">Add a customer</h2>
        <p className="mt-1 text-sm text-slate-600">
          Ask your customer for the share code on their profile page. They control who can see
          their data.
        </p>
        <form onSubmit={linkCustomer} className="mt-4 flex flex-wrap gap-2">
          <input
            value={shareCode}
            onChange={(e) => setShareCode(e.target.value)}
            className="input flex-1 font-mono uppercase tracking-widest sm:max-w-xs sm:flex-none"
            placeholder="ABCD1234"
            maxLength={12}
            required
          />
          <button type="submit" className="btn-primary" disabled={linking}>
            {linking ? "Adding…" : "Add customer"}
          </button>
        </form>
        {linkError && <p className="mt-2 text-sm text-red-600">{linkError}</p>}
        {linkNotice && <p className="mt-2 text-sm text-emerald-600">{linkNotice}</p>}
      </section>

      <section>
        <h2 className="text-xl font-semibold">Your roster</h2>
        {customers.length === 0 ? (
          <p className="card mt-4 text-slate-500">
            No customers yet. Add someone using their share code above.
          </p>
        ) : (
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            {customers.map((customer) => (
              <article key={customer.id} className="card">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="break-words font-semibold text-slate-900">{customer.full_name}</h3>
                    <p className="truncate text-sm text-slate-500">{customer.email}</p>
                  </div>
                  {customer.primary_goal && (
                    <span className="shrink-0 rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
                      {goalLabels[customer.primary_goal] ?? customer.primary_goal}
                    </span>
                  )}
                </div>

                {customer.profile_completed ? (
                  <dl className="mt-4 grid grid-cols-3 gap-2 text-center text-sm">
                    <div className="rounded-lg bg-slate-50 py-2">
                      <dt className="text-xs text-slate-500">Age</dt>
                      <dd className="font-semibold">{customer.age}</dd>
                    </div>
                    <div className="rounded-lg bg-slate-50 py-2">
                      <dt className="text-xs text-slate-500">Weight</dt>
                      <dd className="font-semibold">{customer.weight_kg} kg</dd>
                    </div>
                    <div className="rounded-lg bg-slate-50 py-2">
                      <dt className="text-xs text-slate-500">BMI</dt>
                      <dd className="font-semibold">{customer.bmi}</dd>
                    </div>
                  </dl>
                ) : (
                  <p className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700">
                    Profile incomplete — plans can&apos;t be generated yet.
                  </p>
                )}

                <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
                  <span className="flex flex-wrap items-center gap-2 text-sm text-slate-500">
                    {customer.workout_plan_count} workout · {customer.diet_plan_count} diet
                    {customer.pending_requests > 0 && (
                      <Link
                        to="/requests"
                        className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 hover:bg-amber-200"
                      >
                        {customer.pending_requests} pending request
                        {customer.pending_requests === 1 ? "" : "s"}
                      </Link>
                    )}
                  </span>
                  <Link to={`/customers/${customer.id}`} className="btn-primary">
                    Open
                  </Link>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
