import { useState, type FormEvent } from "react";
import { api } from "../lib/api";
import type { CustomerRequest } from "../lib/requests";
import NutritionItemsEditor, {
  blankItem,
  itemFromDraft,
  type ItemDraft,
} from "./NutritionItemsEditor";
import { mealKey } from "./WeeklyDietPlan";

interface MealDraft {
  day: string;
  session: string;
  kept: string[];
  removed: string[];
  items: ItemDraft[];
}

interface Props {
  request: CustomerRequest;
  onDone: () => Promise<void>;
}

function FoodList({ label, foods, className }: { label: string; foods: string[]; className: string }) {
  if (foods.length === 0) return null;
  return (
    <p className="text-sm">
      <span className="font-medium text-slate-600">{label}: </span>
      {foods.map((food) => (
        <span key={food} className={`mr-1.5 inline-block rounded-full px-2 py-0.5 text-xs ${className}`}>
          {food}
        </span>
      ))}
    </p>
  );
}

/** Coach form for a customer's meal request: only the foods they added need nutrition values. */
export default function DietRequestReview({ request, onDone }: Props) {
  const [meals, setMeals] = useState<MealDraft[]>(() =>
    (request.requested_meals ?? []).map((meal) => ({
      day: meal.day,
      session: meal.session,
      kept: meal.kept ?? [],
      removed: meal.removed ?? [],
      items: (meal.added ?? meal.items).map((name) => blankItem(name)),
    })),
  );
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<"approve-meal" | "reject" | null>(null);

  const updateItems = (mealIndex: number, items: ItemDraft[]) =>
    setMeals((prev) => prev.map((meal, i) => (i === mealIndex ? { ...meal, items } : meal)));

  const run = async (action: "approve-meal" | "reject", body: unknown) => {
    setError("");
    setBusy(action);
    try {
      await api.post(`/requests/${request.id}/${action}`, body);
      await onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save your review");
      setBusy(null);
    }
  };

  const approve = (event: FormEvent) => {
    event.preventDefault();
    const empty = meals.find((meal) => meal.kept.length === 0 && meal.items.length === 0);
    if (empty) {
      setError(`${empty.day} ${empty.session} needs at least one food.`);
      return;
    }
    void run("approve-meal", {
      note,
      meals: meals.map((meal) => ({
        day: meal.day,
        session: meal.session,
        items: meal.items.map(itemFromDraft),
      })),
    });
  };

  return (
    <form onSubmit={approve} className="space-y-4">
      <p className="text-sm text-slate-600">
        Only the foods the customer added need values. Foods they kept stay as they are, and
        removed foods are dropped when you approve.
      </p>

      {meals.map((meal, mealIndex) => (
        <section
          key={mealKey(meal.day, meal.session)}
          className="space-y-3 rounded-xl border border-slate-200 bg-white p-3 sm:p-4"
        >
          <h4 className="font-semibold text-slate-900">
            {meal.day} · {meal.session}
          </h4>
          <div className="space-y-1">
            <FoodList label="Keeping" foods={meal.kept} className="bg-slate-100 text-slate-700" />
            <FoodList
              label="Removing"
              foods={meal.removed}
              className="bg-rose-50 text-rose-700 line-through"
            />
          </div>

          {meal.items.length > 0 ? (
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
              New foods — set portions and nutrition
            </p>
          ) : (
            <p className="text-sm text-slate-500">No new foods to add for this meal.</p>
          )}
          <NutritionItemsEditor
            items={meal.items}
            onChange={(items) => updateItems(mealIndex, items)}
            idPrefix={`${request.id}-${mealIndex}`}
            minItems={0}
          />
        </section>
      ))}

      <div>
        <label className="label" htmlFor={`${request.id}-note`}>
          Note to customer <span className="font-normal text-slate-500">(optional)</span>
        </label>
        <textarea
          id={`${request.id}-note`}
          rows={2}
          maxLength={500}
          className="input bg-white"
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <button
          type="button"
          className="btn-secondary"
          disabled={busy !== null}
          onClick={() => void run("reject", { note })}
        >
          {busy === "reject" ? "Declining…" : "Decline"}
        </button>
        <button type="submit" className="btn-primary" disabled={busy !== null}>
          {busy === "approve-meal" ? "Approving…" : "Approve and update plan"}
        </button>
      </div>
    </form>
  );
}
