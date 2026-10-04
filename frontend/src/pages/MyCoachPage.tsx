import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";

interface CoachInfo {
  full_name: string;
  email: string;
  specialization: string | null;
  years_experience: number | null;
  bio: string | null;
}

export default function MyCoachPage() {
  const { user } = useAuth();
  const [coach, setCoach] = useState<CoachInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (user?.role !== "customer") return;
    api
      .get<CoachInfo | null>("/plans/my-coach")
      .then(setCoach)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load your coach"))
      .finally(() => setLoading(false));
  }, []);

  if (user?.role !== "customer") {
    return <p className="py-20 text-center text-slate-500">This page is for customers.</p>;
  }
  if (loading) return <p className="py-20 text-center text-slate-500">Loading…</p>;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold sm:text-3xl">My coach</h1>
        <p className="mt-1 text-slate-600">The person who builds and reviews your plans.</p>
      </header>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {coach ? (
        <article className="card">
          <div className="flex flex-wrap items-center gap-4">
            <span className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-indigo-600 text-xl font-bold text-white">
              {coach.full_name
                .split(" ")
                .map((part) => part[0])
                .join("")
                .slice(0, 2)
                .toUpperCase()}
            </span>
            <div className="min-w-0">
              <h2 className="text-xl font-semibold text-slate-900">{coach.full_name}</h2>
              <p className="break-all text-sm text-slate-600">{coach.email}</p>
            </div>
          </div>

          <dl className="mt-6 grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl bg-slate-50 p-4">
              <dt className="text-xs uppercase tracking-wide text-slate-500">Specialization</dt>
              <dd className="mt-1 font-medium text-slate-900">{coach.specialization ?? "—"}</dd>
            </div>
            <div className="rounded-xl bg-slate-50 p-4">
              <dt className="text-xs uppercase tracking-wide text-slate-500">Experience</dt>
              <dd className="mt-1 font-medium text-slate-900">
                {coach.years_experience !== null ? `${coach.years_experience} years` : "—"}
              </dd>
            </div>
          </dl>

          {coach.bio && (
            <section className="mt-6">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">About</h3>
              <p className="mt-2 whitespace-pre-line text-slate-700">{coach.bio}</p>
            </section>
          )}

          <div className="mt-6 flex flex-col gap-2 sm:flex-row">
            <Link to="/requests" className="btn-primary">
              Send a request
            </Link>
            <Link to="/diet-plan" className="btn-secondary">
              Request meal changes
            </Link>
            <a href={`mailto:${coach.email}`} className="btn-soft">
              Email coach
            </a>
          </div>
        </article>
      ) : (
        <div className="card">
          <h2 className="font-semibold">You don&apos;t have a coach yet</h2>
          <p className="mt-2 text-sm text-slate-600">
            Share the code on your profile page with a coach so they can add you and start
            building your plans.
          </p>
          <Link to="/profile" className="btn-primary mt-4">
            Get my share code
          </Link>
        </div>
      )}
    </div>
  );
}
