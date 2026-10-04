import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import AccountEditor from "../components/AccountEditor";
import HealthMetricsPanel from "../components/HealthMetricsPanel";
import MeasurementLogCard from "../components/MeasurementLogCard";
import { useAuth, type User } from "../context/AuthContext";
import { api } from "../lib/api";

const activityLevels = [
  { value: "sedentary", label: "Sedentary (little or no exercise)" },
  { value: "light", label: "Light (1–3 days/week)" },
  { value: "moderate", label: "Moderate (3–5 days/week)" },
  { value: "active", label: "Active (6–7 days/week)" },
  { value: "very_active", label: "Very active (physical job or 2x/day)" },
];

const goals = [
  {
    value: "lose_fat",
    label: "Lose fat",
    description: "Calorie deficit with high protein to keep muscle while losing fat.",
  },
  {
    value: "build_muscle",
    label: "Build muscle",
    description: "Moderate surplus and heavier lifting to add size and strength.",
  },
  {
    value: "maintain",
    label: "Maintain weight",
    description: "Eat around maintenance and keep your current shape and fitness.",
  },
  {
    value: "improve_endurance",
    label: "Improve endurance",
    description: "Carb-focused fuelling with running and conditioning sessions.",
  },
];

// Diet types from the BRD (section 4.1.5).
const dietTypes = [
  { value: "vegetarian", label: "Vegetarian — no meat, fish or eggs" },
  { value: "eggetarian", label: "Eggetarian — vegetarian plus eggs" },
  { value: "non_vegetarian", label: "Non-vegetarian — includes meat and fish" },
  { value: "vegan", label: "Vegan — no animal products at all" },
];

/** Turns "vegan, no dairy" into ["vegan", "no dairy"]. */
function toList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

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

function CustomerForm({ user }: { user: User }) {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const isFirstTime = !user.profile_completed;
  const profile = user.customer;

  const [form, setForm] = useState({
    height_cm: profile?.height_cm?.toString() ?? "",
    weight_kg: profile?.weight_kg?.toString() ?? "",
    waist_cm: profile?.waist_cm?.toString() ?? "",
    neck_cm: profile?.neck_cm?.toString() ?? "",
    hip_cm: profile?.hip_cm?.toString() ?? "",
    activity_level: profile?.activity_level ?? "moderate",
    primary_goal: profile?.primary_goal ?? "lose_fat",
    diet_type: profile?.diet_type ?? "non_vegetarian",
    dietary_preferences: profile?.dietary_preferences?.join(", ") ?? "",
    health_injury_history: profile?.health_injury_history?.join(", ") ?? "",
  });
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const update = (field: keyof typeof form, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setStatus("");
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      const updated = await api.put<User>("/auth/me/customer-profile", {
        height_cm: Number(form.height_cm),
        weight_kg: Number(form.weight_kg),
        waist_cm: form.waist_cm ? Number(form.waist_cm) : null,
        neck_cm: form.neck_cm ? Number(form.neck_cm) : null,
        hip_cm: form.hip_cm ? Number(form.hip_cm) : null,
        activity_level: form.activity_level,
        primary_goal: form.primary_goal,
        diet_type: form.diet_type,
        dietary_preferences: toList(form.dietary_preferences),
        health_injury_history: toList(form.health_injury_history),
      });
      setUser(updated);
      if (isFirstTime) navigate("/workout-plan", { replace: true });
      else setStatus("Profile saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save profile");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <form onSubmit={handleSubmit} className="card space-y-5 lg:col-span-2">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="height">
              Height (cm)
            </label>
            <input
              id="height"
              type="number"
              min={100}
              max={250}
              step="0.1"
              required
              value={form.height_cm}
              onChange={(e) => update("height_cm", e.target.value)}
              className="input"
              placeholder="175"
            />
          </div>

          <div>
            <label className="label" htmlFor="weight">
              Weight (kg)
            </label>
            <input
              id="weight"
              type="number"
              min={30}
              max={250}
              step="0.1"
              required
              value={form.weight_kg}
              onChange={(e) => update("weight_kg", e.target.value)}
              className="input"
              placeholder="72"
            />
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className="label" htmlFor="waist">
              Waist (cm)
            </label>
            <input
              id="waist"
              type="number"
              min={40}
              max={200}
              step="0.1"
              value={form.waist_cm}
              onChange={(e) => update("waist_cm", e.target.value)}
              className="input"
              placeholder="92"
            />
          </div>
          <div>
            <label className="label" htmlFor="neck">
              Neck (cm)
            </label>
            <input
              id="neck"
              type="number"
              min={20}
              max={60}
              step="0.1"
              value={form.neck_cm}
              onChange={(e) => update("neck_cm", e.target.value)}
              className="input"
              placeholder="39"
            />
          </div>
          <div>
            <label className="label" htmlFor="hip">
              Hip (cm)
            </label>
            <input
              id="hip"
              type="number"
              min={40}
              max={200}
              step="0.1"
              value={form.hip_cm}
              onChange={(e) => update("hip_cm", e.target.value)}
              className="input"
              placeholder="96"
            />
          </div>
        </div>
        <p className="-mt-2 text-xs text-slate-500">
          Waist and neck power your body fat estimate. Hip is only used for women.
        </p>

        <div>
          <label className="label" htmlFor="activity">
            Activity level
          </label>
          <select
            id="activity"
            value={form.activity_level}
            onChange={(e) => update("activity_level", e.target.value)}
            className="input"
          >
            {activityLevels.map((level) => (
              <option key={level.value} value={level.value}>
                {level.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <span className="label">Primary goal</span>
          <div className="grid gap-2 sm:grid-cols-2">
            {goals.map((goal) => (
              <button
                key={goal.value}
                type="button"
                onClick={() => update("primary_goal", goal.value)}
                className={`rounded-xl border p-3 text-left transition ${
                  form.primary_goal === goal.value
                    ? "border-indigo-500 bg-indigo-50"
                    : "border-slate-300 hover:bg-slate-50"
                }`}
              >
                <span className="block font-medium text-slate-900">{goal.label}</span>
                <span className="mt-1 block text-xs text-slate-600">{goal.description}</span>
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="label" htmlFor="diet_type">
            Dietary preference
          </label>
          <select
            id="diet_type"
            value={form.diet_type}
            onChange={(e) => update("diet_type", e.target.value)}
            className="input"
          >
            {dietTypes.map((diet) => (
              <option key={diet.value} value={diet.value}>
                {diet.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="label" htmlFor="diet">
            Allergies & restrictions
          </label>
          <input
            id="diet"
            value={form.dietary_preferences}
            onChange={(e) => update("dietary_preferences", e.target.value)}
            className="input"
            placeholder="no dairy, peanut allergy, gluten free"
          />
          <p className="mt-1 text-xs text-slate-500">Separate with commas.</p>
        </div>

        <div>
          <label className="label" htmlFor="injuries">
            Health / injury history
          </label>
          <input
            id="injuries"
            value={form.health_injury_history}
            onChange={(e) => update("health_injury_history", e.target.value)}
            className="input"
            placeholder="lower back pain, knee surgery"
          />
          <p className="mt-1 text-xs text-slate-500">Separate with commas.</p>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex items-center gap-3">
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? "Saving…" : isFirstTime ? "Save and continue" : "Save profile"}
          </button>
          {status && <span className="text-sm text-emerald-600">{status}</span>}
        </div>
      </form>

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
            <aside>
              <AccountCard user={user} />
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

      {!isCoach && (
        <section className="card">
          <h2 className="text-xl font-semibold">Health metrics</h2>
          <p className="mt-1 text-sm text-slate-600">
            Calculated from your measurements, activity level and goal.
          </p>
          <div className="mt-5">
            {user.metrics ? (
              <HealthMetricsPanel metrics={user.metrics} />
            ) : (
              <p className="text-sm text-slate-500">
                Save your profile to see your full health metrics.
              </p>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
