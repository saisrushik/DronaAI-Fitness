import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import AccountEditor from "../components/AccountEditor";
import AccountPrivacyCard from "../components/AccountPrivacyCard";
import MeasurementLogCard from "../components/MeasurementLogCard";
import OnboardingWizard from "../components/OnboardingWizard";
import {
  ActivitySection,
  BodySection,
  DietSection,
  draftFromProfile,
  GoalSection,
  HealthSection,
  payloadFromDraft,
  TrainingSection,
  type ProfileDraft,
  type UpdateDraft,
} from "../components/ProfileSections";
import UnitToggle from "../components/UnitToggle";
import { useAuth, type User } from "../context/AuthContext";
import { api } from "../lib/api";
import { labelFor } from "../lib/profileOptions";

function ageFrom(dob: string): number {
  const birth = new Date(dob);
  const today = new Date();
  const hadBirthday =
    today.getMonth() > birth.getMonth() ||
    (today.getMonth() === birth.getMonth() && today.getDate() >= birth.getDate());
  return today.getFullYear() - birth.getFullYear() - (hadBirthday ? 0 : 1);
}

function AccountCard({ user }: { user: User }) {
  const [editing, setEditing] = useState(false);
  const profile = user.role === "coach" ? user.coach : user.customer;
  const rows: [string, string][] = [
    ["Name", user.full_name],
    ["Email", user.email],
    ["Role", user.role === "coach" ? "Coach" : "Customer"],
    ["Gender", profile?.gender ? profile.gender[0].toUpperCase() + profile.gender.slice(1) : "—"],
    [
      "Date of birth",
      profile?.date_of_birth ? new Date(profile.date_of_birth).toLocaleDateString() : "—",
    ],
    ["Age", profile?.date_of_birth ? String(ageFrom(profile.date_of_birth)) : "—"],
    ...(user.role === "customer" && user.customer
      ? ([["Country", labelFor("country", user.customer.country)]] as [string, string][])
      : []),
  ];

  return (
    <div className="card">
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-semibold">Account</h2>
        <button type="button" className="btn-soft btn-sm" onClick={() => setEditing(true)}>
          <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 3.5a2.1 2.1 0 013 3L7 19l-4 1 1-4 12.5-12.5z" />
          </svg>
          Edit details
        </button>
      </div>
      <dl className="mt-3 space-y-2 text-sm">
        {rows.map(([label, value]) => (
          <div key={label} className="flex justify-between gap-4">
            <dt className="shrink-0 text-slate-500">{label}</dt>
            <dd className="min-w-0 truncate text-right font-medium" title={value}>
              {value}
            </dd>
          </div>
        ))}
      </dl>
      <div className="mt-4 border-t border-slate-100 pt-3">
        <p className="mb-2 text-xs font-medium text-slate-500">Units</p>
        <UnitToggle />
      </div>
      {editing && <AccountEditor user={user} onClose={() => setEditing(false)} />}
    </div>
  );
}

function CoachForm({ user }: { user: User }) {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const isFirstTime = !user.profile_completed;

  const [form, setForm] = useState({
    specialization: user.coach?.specialization ?? "",
    years_experience: user.coach?.years_experience?.toString() ?? "",
    bio: user.coach?.bio ?? "",
  });
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      const updated = await api.put<User>("/auth/me/coach-profile", {
        specialization: form.specialization,
        years_experience: Number(form.years_experience),
        bio: form.bio,
      });
      setUser(updated);
      if (isFirstTime) navigate("/customers", { replace: true });
      else setStatus("Profile saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save profile");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="card space-y-5 lg:col-span-2">
      <div>
        <label className="label" htmlFor="specialization">
          Specialization
        </label>
        <input
          id="specialization"
          required
          value={form.specialization}
          onChange={(e) => setForm({ ...form, specialization: e.target.value })}
          className="input"
          placeholder="Strength & conditioning"
        />
      </div>

      <div>
        <label className="label" htmlFor="experience">
          Years of experience
        </label>
        <input
          id="experience"
          type="number"
          min={0}
          max={60}
          required
          value={form.years_experience}
          onChange={(e) => setForm({ ...form, years_experience: e.target.value })}
          className="input"
          placeholder="5"
        />
      </div>

      <div>
        <label className="label" htmlFor="bio">
          Short bio
        </label>
        <textarea
          id="bio"
          rows={4}
          maxLength={500}
          value={form.bio}
          onChange={(e) => setForm({ ...form, bio: e.target.value })}
          className="input"
          placeholder="Tell your customers about your coaching approach."
        />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex items-center gap-3">
        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? "Saving…" : isFirstTime ? "Save and continue" : "Save profile"}
        </button>
        {status && <span className="text-sm text-emerald-600">{status}</span>}
      </div>
    </form>
  );
}

function FormSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-3 border-t border-slate-100 pt-5 first:border-t-0 first:pt-0">
      <h2 className="font-semibold text-slate-900">{title}</h2>
      {children}
    </section>
  );
}

function CustomerForm({ user }: { user: User }) {
  const { setUser } = useAuth();
  const isFirstTime = !user.profile_completed;
  const hasCoach = !!user.customer?.coach_id;

  const [draft, setDraft] = useState<ProfileDraft>(() => draftFromProfile(user.customer));
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const update: UpdateDraft = (field, value) => {
    setDraft((prev) => ({ ...prev, [field]: value }));
    setStatus("");
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      const updated = await api.put<User>("/auth/me/customer-profile", payloadFromDraft(draft));
      setUser(updated);
      setStatus(
        hasCoach
          ? "Profile saved. Your coach has been told about any changes so they can update your plans."
          : "Profile saved.",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save profile");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      {isFirstTime ? (
        <OnboardingWizard user={user} />
      ) : (
        <form onSubmit={handleSubmit} className="card space-y-5 lg:col-span-2">
          <FormSection title="Body measurements">
            <BodySection draft={draft} update={update} />
          </FormSection>
          <FormSection title="Activity level">
            <ActivitySection draft={draft} update={update} />
          </FormSection>
          <FormSection title="Primary goal">
            <GoalSection draft={draft} update={update} />
          </FormSection>
          <FormSection title="Diet">
            <DietSection draft={draft} update={update} />
          </FormSection>
          <FormSection title="Health & injuries">
            <HealthSection draft={draft} update={update} />
          </FormSection>
          <FormSection title="Workout preferences">
            <TrainingSection draft={draft} update={update} />
          </FormSection>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="sticky bottom-0 -mx-4 flex flex-wrap items-center gap-3 border-t border-slate-100 bg-white/95 px-4 py-3 backdrop-blur sm:-mx-6 sm:px-6">
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? "Saving…" : "Save profile"}
            </button>
            {status && <span className="text-sm text-emerald-600">{status}</span>}
          </div>
        </form>
      )}
      <aside className="space-y-4">
        <AccountCard user={user} />
        {/* Only needed until a coach links the customer; reappears if the coach removes them. */}
        {!user.customer?.coach_id && (
          <div className="card">
            <h2 className="font-semibold">Your share code</h2>
            <p className="mt-1 text-sm text-slate-600">
              Give this to a coach so they can add you. Only share it with someone you want to see
              your health data.
            </p>
            <p className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-center font-mono text-xl tracking-widest text-slate-900">
              {user.customer?.share_code ?? "—"}
            </p>
          </div>
        )}
        <AccountPrivacyCard user={user} />
      </aside>
    </>
  );
}

export default function ProfilePage() {
  const { user, setUser } = useAuth();

  // Pick up changes made by others since login, such as a coach adding or removing this customer.
  useEffect(() => {
    api
      .get<User>("/auth/me")
      .then(setUser)
      .catch(() => undefined);
  }, [setUser]);

  if (!user) return null;

  const isCoach = user.role === "coach";
  const isFirstTime = !user.profile_completed;
  const c = user.customer;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold sm:text-3xl">
          {isFirstTime ? `Welcome, ${user.full_name}!` : "Your profile"}
        </h1>
        <p className="mt-1 text-slate-600">
          {isFirstTime
            ? isCoach
              ? "Tell your customers a bit about your coaching background."
              : "Tell us about yourself so your coach can build your plans."
            : isCoach
              ? "This is what your customers see about you."
              : "These details drive your calorie targets and plan recommendations."}
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-3">
        {isCoach ? (
          <>
            <CoachForm user={user} />
            <aside className="space-y-4">
              <AccountCard user={user} />
              <AccountPrivacyCard user={user} />
            </aside>
          </>
        ) : (
          // Remount when logged measurements change so the form never saves stale values.
          <CustomerForm
            key={[c?.weight_kg, c?.height_cm, c?.waist_cm, c?.neck_cm, c?.hip_cm].join("|")}
            user={user}
          />
        )}
      </div>

      {!isCoach && !isFirstTime && <MeasurementLogCard />}

      {!isCoach && !isFirstTime && user.metrics && (
        <Link
          to="/stats"
          className="card flex flex-wrap items-center justify-between gap-3 transition hover:border-indigo-300"
        >
          <div>
            <h2 className="text-xl font-semibold">Health metrics</h2>
            <p className="mt-1 text-sm text-slate-600">
              BMI {user.metrics.bmi.value} · {user.metrics.target_calories} kcal a day ·{" "}
              {user.metrics.macros.protein_g}g protein. See all 10 calculators and how each is
              worked out.
            </p>
          </div>
          <span className="btn-soft">Open My Stats &rarr;</span>
        </Link>
      )}
    </div>
  );
}
