import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Modal from "../components/Modal";
import { useAuth, type User } from "../context/AuthContext";
import { api } from "../lib/api";

interface CoachInfo {
  full_name: string;
  email: string;
  specialization: string | null;
  years_experience: number | null;
  bio: string | null;
}

function LeaveCoachModal({
  coach,
  onClose,
  onLeft,
}: {
  coach: CoachInfo;
  onClose: () => void;
  onLeft: () => void;
}) {
  const [error, setError] = useState("");
  const [leaving, setLeaving] = useState(false);

  const leave = async () => {
    setError("");
    setLeaving(true);
    try {
      await api.post("/plans/my-coach/leave");
      onLeft();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not leave your coach");
      setLeaving(false);
    }
  };

  return (
    <Modal
      onClose={onClose}
      title={<h2 className="text-lg font-semibold text-slate-900">Leave {coach.full_name}?</h2>}
    >
      <div className="space-y-4 text-sm text-slate-700">
        <ul className="list-disc space-y-1 pl-5">
          <li>{coach.full_name} immediately loses access to your profile and progress.</li>
          <li>Requests still waiting for a reply are closed.</li>
          <li>You keep your plans, measurements and progress history.</li>
          <li>To switch coach, give your share code to the new coach afterwards.</li>
        </ul>
        {error && <p className="text-red-600">{error}</p>}
        <div className="flex flex-col-reverse gap-2 border-t border-slate-100 pt-4 sm:flex-row sm:justify-end">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Stay with my coach
          </button>
          <button type="button" className="btn-danger" onClick={leave} disabled={leaving}>
            {leaving ? "Leaving…" : "Leave coach"}
          </button>
        </div>
      </div>
    </Modal>
  );
}

export default function MyCoachPage() {
  const { user, setUser } = useAuth();
  const [coach, setCoach] = useState<CoachInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [confirmLeave, setConfirmLeave] = useState(false);
  const [notice, setNotice] = useState("");

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

  const onLeft = async () => {
    setConfirmLeave(false);
    setCoach(null);
    setNotice("You left your coach. Share your code below with a new coach to continue.");
    // coach_id drives what the rest of the app shows, so pick up the change right away.
    await api
      .get<User>("/auth/me")
      .then(setUser)
      .catch(() => undefined);
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold sm:text-3xl">My coach</h1>
        <p className="mt-1 text-slate-600">The person who builds and reviews your plans.</p>
      </header>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {notice && (
        <p className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{notice}</p>
      )}

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

          <div className="mt-6 flex flex-col gap-3 border-t border-slate-100 pt-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-slate-500">
              Want to change coach? Leave first, then share your code with the new one.
            </p>
            <button
              type="button"
              className="btn shrink-0 border border-red-200 bg-white text-red-700 hover:bg-red-50"
              onClick={() => setConfirmLeave(true)}
            >
              Leave coach
            </button>
          </div>
          {confirmLeave && (
            <LeaveCoachModal coach={coach} onClose={() => setConfirmLeave(false)} onLeft={onLeft} />
          )}
        </article>
      ) : (
        <div className="card">
          <h2 className="font-semibold">You don&apos;t have a coach yet</h2>
          <p className="mt-2 text-sm text-slate-600">
            Give this code to a coach so they can add you and start building your plans. Only share
            it with someone you want to see your health data.
          </p>
          <p className="mt-4 rounded-lg bg-slate-50 px-3 py-2 text-center font-mono text-xl tracking-widest text-slate-900 sm:max-w-xs">
            {user.customer?.share_code ?? "—"}
          </p>
        </div>
      )}
    </div>
  );
}
