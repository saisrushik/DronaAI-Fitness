import { useState } from "react";
import { Link } from "react-router-dom";
import { useNotifications } from "../context/NotificationsContext";
import { api } from "../lib/api";
import { requestLink, type CustomerRequest } from "../lib/requests";
import PlanCard, { type Plan } from "./PlanCard";
import type { WeeklyDietContent } from "./WeeklyDietPlan";

interface Props {
  plan: Plan;
  /** This plan's meal requests, newest first. */
  requests: CustomerRequest[];
  hasCoach: boolean;
  onChanged: () => Promise<void>;
}

export default function EditableDietPlan({ plan, requests, hasCoach, onChanged }: Props) {
  const { refresh: refreshNotifications } = useNotifications();
  const [editing, setEditing] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, string[]>>({});
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const pending = requests.find((r) => r.status === "pending");
  const content = plan.content as WeeklyDietContent;

  const setDraft = (key: string, items: string[] | null) =>
    setDrafts((prev) => {
      const next = { ...prev };
      if (items === null) delete next[key];
      else next[key] = items;
      return next;
    });

  const changes = Object.entries(drafts)
    .map(([key, items]) => {
      const [day, session] = key.split("|");
      return { day, session, items: items.map((item) => item.trim()).filter(Boolean) };
    })
    .filter((meal) => {
      const original = content.days
        .find((d) => d.day === meal.day)
        ?.sessions.find((s) => s.name === meal.session)
        ?.items.map((item) => item.name);
      return meal.items.length > 0 && meal.items.join("\n") !== original?.join("\n");
    });
  const hasEmptyMeal = Object.values(drafts).some((items) => items.every((item) => !item.trim()));

  const stopEditing = () => {
    setEditing(false);
    setDrafts({});
    setNote("");
    setError("");
  };

  const submit = async () => {
    setError("");
    setSubmitting(true);
    try {
      await api.post("/requests/meal", { plan_id: plan.id, meals: changes, description: note });
      stopEditing();
      await Promise.all([onChanged(), refreshNotifications().catch(() => undefined)]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit your meal request");
    } finally {
      setSubmitting(false);
    }
  };

  const headerAction = pending ? (
    <Link
      to={requestLink(pending.id)}
      className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800 hover:bg-amber-200"
    >
      Meal request pending &rarr;
    </Link>
  ) : editing ? null : (
    <button
      type="button"
      className="btn-secondary w-full sm:w-auto"
      onClick={() => setEditing(true)}
      disabled={!hasCoach}
      title={hasCoach ? undefined : "You need a coach to review meal changes"}
    >
      Edit meals
    </button>
  );

  return (
    <div className="space-y-3">
      <PlanCard
        plan={plan}
        headerAction={headerAction}
        dietEdit={editing ? { drafts, setDraft } : undefined}
      >
        {editing && (
          <div className="mt-4 space-y-3 rounded-xl bg-indigo-50 p-4 text-sm text-indigo-900">
            <p>
              Tap <span className="font-semibold">Edit</span> on any meal to swap foods. Just name
              the foods &mdash; your coach sets the quantities, calories and macros before it goes
              into your plan.
            </p>
            <div>
              <label className="label" htmlFor={`note-${plan.id}`}>
                Note for your coach <span className="font-normal text-slate-500">(optional)</span>
              </label>
              <textarea
                id={`note-${plan.id}`}
                rows={2}
                maxLength={1000}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                className="input bg-white"
                placeholder="e.g. I prefer South Indian breakfasts"
              />
            </div>
          </div>
        )}
      </PlanCard>

      {editing && (
        <div className="sticky bottom-3 z-10 space-y-2 rounded-2xl border border-indigo-200 bg-white p-3 shadow-lg">
          {hasEmptyMeal && (
            <p className="text-xs text-amber-700">
              Meals with no foods are ignored. Add a food or undo the change.
            </p>
          )}
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm text-slate-600">
              {changes.length === 0
                ? "No changes yet"
                : `${changes.length} meal${changes.length === 1 ? "" : "s"} changed`}
            </span>
            <div className="flex shrink-0 gap-2">
              <button type="button" className="btn-secondary" onClick={stopEditing}>
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={submit}
                disabled={changes.length === 0 || submitting}
              >
                {submitting ? "Submitting…" : "Submit meal request"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
