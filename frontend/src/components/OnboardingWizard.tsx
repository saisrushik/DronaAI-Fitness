import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth, type User } from "../context/AuthContext";
import { api } from "../lib/api";
import { describeInjury, labelFor } from "../lib/profileOptions";
import { formatHeight, formatLength, formatWeight, useUnitSystem } from "../lib/units";
import {
  ActivitySection,
  BodySection,
  DietSection,
  draftFromProfile,
  GoalSection,
  HealthSection,
  payloadFromDraft,
  toList,
  TrainingSection,
  type ProfileDraft,
  type UpdateDraft,
} from "./ProfileSections";

interface Step {
  title: string;
  description: string;
  render: (draft: ProfileDraft, update: UpdateDraft) => ReactNode;
}

// FR-1.5 order. Demographics were collected at sign-up.
const STEPS: Step[] = [
  {
    title: "Your body",
    description: "These measurements drive your BMI, body fat and calorie targets.",
    render: (draft, update) => <BodySection draft={draft} update={update} />,
  },
  {
    title: "Activity",
    description: "How active are you outside of planned workouts?",
    render: (draft, update) => <ActivitySection draft={draft} update={update} />,
  },
  {
    title: "Goal",
    description: "Your goal sets your calorie target, protein and training style.",
    render: (draft, update) => <GoalSection draft={draft} update={update} />,
  },
  {
    title: "Diet",
    description: "So your meals match what you eat and can buy.",
    render: (draft, update) => <DietSection draft={draft} update={update} />,
  },
  {
    title: "Health & injuries",
    description: "Keeps your plans safe. Your coach sees this.",
    render: (draft, update) => <HealthSection draft={draft} update={update} />,
  },
  {
    title: "Workout preferences",
    description: "Shapes how often, where and how hard you train.",
    render: (draft, update) => <TrainingSection draft={draft} update={update} />,
  },
];
const REVIEW = STEPS.length;

function ReviewRow({ label, value, onEdit }: { label: string; value: string; onEdit: () => void }) {
  return (
    <div className="flex items-start justify-between gap-4 py-2.5 text-sm">
      <dt className="w-32 shrink-0 text-slate-500 sm:w-40">{label}</dt>
      <dd className="min-w-0 flex-1 break-words font-medium text-slate-800">{value}</dd>
      <button type="button" onClick={onEdit} className="shrink-0 text-xs font-medium text-indigo-600 hover:underline">
        Edit
      </button>
    </div>
  );
}

function Review({ draft, goTo }: { draft: ProfileDraft; goTo: (step: number) => void }) {
  const system = useUnitSystem();
  const length = (value: string) => (value ? formatLength(Number(value), system) : "—");
  const restrictions = toList(draft.dietary_preferences);
  return (
    <dl className="divide-y divide-slate-100">
      <ReviewRow
        label="Body"
        value={`${formatHeight(Number(draft.height_cm), system)}, ${formatWeight(
          Number(draft.weight_kg),
          system,
        )} · waist ${length(draft.waist_cm)} · neck ${length(draft.neck_cm)} · hip ${length(draft.hip_cm)}`}
        onEdit={() => goTo(0)}
      />
      <ReviewRow label="Activity" value={labelFor("activity", draft.activity_level)} onEdit={() => goTo(1)} />
      <ReviewRow label="Goal" value={labelFor("goal", draft.primary_goal)} onEdit={() => goTo(2)} />
      <ReviewRow
        label="Diet"
        value={`${labelFor("diet", draft.diet_type)} · ${labelFor("budget", draft.budget_level)} budget${
          restrictions.length ? ` · ${restrictions.join(", ")}` : ""
        }`}
        onEdit={() => goTo(3)}
      />
      <ReviewRow
        label="Medical conditions"
        value={draft.medical_conditions.map((c) => labelFor("condition", c)).join(", ") || "None"}
        onEdit={() => goTo(4)}
      />
      <ReviewRow label="Stress" value={labelFor("stress", draft.stress_level)} onEdit={() => goTo(4)} />
      <ReviewRow
        label="Injuries"
        value={draft.injuries.map(describeInjury).join("; ") || "None"}
        onEdit={() => goTo(4)}
      />
      <ReviewRow
        label="Training"
        value={`${labelFor("experience", draft.training_experience)} · ${labelFor(
          "location",
          draft.training_location,
        )} · ${draft.training_days_per_week} days/week`}
        onEdit={() => goTo(5)}
      />
    </dl>
  );
}

/** First-time customer onboarding (FR-1.5): one step per screen, then a review. */
export default function OnboardingWizard({ user }: { user: User }) {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const storageKey = `onboarding:${user.id}`;

  const [draft, setDraft] = useState<ProfileDraft>(() => {
    const saved = sessionStorage.getItem(storageKey);
    if (saved) {
      try {
        return { ...draftFromProfile(user.customer), ...(JSON.parse(saved) as Partial<ProfileDraft>) };
      } catch {
        sessionStorage.removeItem(storageKey);
      }
    }
    return draftFromProfile(user.customer);
  });
  const [step, setStep] = useState(0);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  // Survives a refresh mid-way; cleared once the profile is saved.
  useEffect(() => {
    sessionStorage.setItem(storageKey, JSON.stringify(draft));
  }, [draft, storageKey]);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [step]);

  const update: UpdateDraft = (field, value) => setDraft((prev) => ({ ...prev, [field]: value }));

  const finish = async () => {
    setError("");
    setSaving(true);
    try {
      const updated = await api.put<User>("/auth/me/customer-profile", payloadFromDraft(draft));
      sessionStorage.removeItem(storageKey);
      setUser(updated);
      navigate("/workout-plan", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save your profile");
      setSaving(false);
    }
  };

  const next = (event: FormEvent) => {
    event.preventDefault();
    if (step === REVIEW) void finish();
    else setStep(step + 1);
  };

  const isReview = step === REVIEW;
  const current = STEPS[step];
  const total = STEPS.length + 1;

  return (
    <form onSubmit={next} className="card space-y-6 lg:col-span-2">
      <div>
        <div className="flex items-center justify-between text-xs font-medium text-slate-500">
          <span>
            Step {step + 1} of {total}
          </span>
          <span>{isReview ? "Review" : current.title}</span>
        </div>
        <div
          className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100"
          role="progressbar"
          aria-valuemin={1}
          aria-valuemax={total}
          aria-valuenow={step + 1}
        >
          <div
            className="h-full rounded-full bg-indigo-600 transition-all"
            style={{ width: `${((step + 1) / total) * 100}%` }}
          />
        </div>
        <ol className="mt-3 hidden flex-wrap gap-1.5 sm:flex">
          {[...STEPS.map((s) => s.title), "Review"].map((title, index) => (
            <li key={title}>
              <button
                type="button"
                // Only steps already reached can be revisited, so required fields stay validated.
                disabled={index > step}
                onClick={() => setStep(index)}
                className={`rounded-full px-2.5 py-1 text-xs font-medium transition ${
                  index === step
                    ? "bg-indigo-600 text-white"
                    : index < step
                      ? "bg-indigo-50 text-indigo-700 hover:bg-indigo-100"
                      : "bg-slate-100 text-slate-400"
                }`}
              >
                {title}
              </button>
            </li>
          ))}
        </ol>
      </div>

      <header>
        <h2 className="text-xl font-semibold">{isReview ? "Check your details" : current.title}</h2>
        <p className="mt-1 text-sm text-slate-600">
          {isReview
            ? "You can change any of this later from your profile."
            : current.description}
        </p>
      </header>

      {isReview ? <Review draft={draft} goTo={setStep} /> : current.render(draft, update)}

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex flex-col-reverse gap-2 border-t border-slate-100 pt-4 sm:flex-row sm:justify-between">
        <button
          type="button"
          className="btn-secondary"
          onClick={() => setStep(step - 1)}
          disabled={step === 0 || saving}
        >
          Back
        </button>
        <button type="submit" className="btn-primary" disabled={saving}>
          {isReview ? (saving ? "Saving…" : "Finish and see my plan") : "Continue"}
        </button>
      </div>
    </form>
  );
}
