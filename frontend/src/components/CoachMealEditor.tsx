import { useState, type FormEvent } from "react";
import { api } from "../lib/api";
import Modal from "./Modal";
import NutritionItemsEditor, { draftFromItem, itemFromDraft } from "./NutritionItemsEditor";
import type { Plan } from "./PlanCard";
import type { DietSession } from "./WeeklyDietPlan";

interface Props {
  plan: Plan;
  day: string;
  session: DietSession;
  onClose: () => void;
  onSaved: () => Promise<void>;
}

/** Lets a coach change the foods in one meal of a diet plan, or delete the meal entirely. */
export default function CoachMealEditor({ plan, day, session, onClose, onSaved }: Props) {
  const [items, setItems] = useState(() => session.items.map(draftFromItem));
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<"save" | "delete" | null>(null);

  const run = async (action: "save" | "delete", call: () => Promise<unknown>) => {
    setError("");
    setBusy(action);
    try {
      await call();
      await onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update the meal");
      setBusy(null);
    }
  };

  const save = (event: FormEvent) => {
    event.preventDefault();
    void run("save", () =>
      api.put(`/coach/plans/${plan.id}/meals`, {
        day,
        session: session.name,
        items: items.map(itemFromDraft),
      }),
    );
  };

  const remove = () => {
    if (!window.confirm(`Delete ${session.name} from ${day}? This updates the customer's plan.`)) {
      return;
    }
    const query = new URLSearchParams({ day, session: session.name });
    void run("delete", () => api.delete(`/coach/plans/${plan.id}/meals?${query}`));
  };

  return (
    <Modal
      onClose={onClose}
      title={
        <>
          <h2 className="text-lg font-semibold text-slate-900">
            Edit {day} · {session.name}
          </h2>
          <p className="text-xs text-slate-500">{plan.title}</p>
        </>
      }
    >
      <form onSubmit={save} className="space-y-4">
        <NutritionItemsEditor
          items={items}
          onChange={setItems}
          idPrefix={`meal-${plan.id}`}
        />

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex flex-col-reverse gap-2 border-t border-slate-100 pt-4 sm:flex-row sm:items-center sm:justify-between">
          <button
            type="button"
            onClick={remove}
            disabled={busy !== null}
            className="btn border border-red-200 bg-white text-red-600 hover:bg-red-50"
          >
            {busy === "delete" ? "Deleting…" : "Delete meal"}
          </button>
          <div className="flex flex-col-reverse gap-2 sm:flex-row">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={busy !== null}>
              {busy === "save" ? "Saving…" : "Save meal"}
            </button>
          </div>
        </div>
      </form>
    </Modal>
  );
}
