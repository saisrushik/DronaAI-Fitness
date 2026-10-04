import { useState } from "react";

export interface Macros {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface DietItem extends Macros {
  name: string;
  quantity: string;
}

export interface DietSession {
  name: string;
  option: string;
  items: DietItem[];
  totals: Macros;
}

export interface DietDay {
  day: string;
  sessions: DietSession[];
  totals: Macros;
}

export interface WeeklyDietContent {
  style: string;
  targets: Macros & { bmi: number; bmr: number; tdee: number; target_calories: number };
  days: DietDay[];
  weekly_totals: Macros;
  daily_average: Macros;
  notes: string;
}

/** Draft food lists keyed by mealKey(); a meal with no draft is unchanged. */
export interface MealEditing {
  drafts: Record<string, string[]>;
  setDraft: (key: string, items: string[] | null) => void;
}

export const MAX_FOODS_PER_MEAL = 12;

export type ManageMeal = (day: string, session: DietSession) => void;

export const mealKey = (day: string, session: string) => `${day}|${session}`;

/** Protein / carbs / fat chips shown at item, session, day and week level. */
export function MacroChips({ macros, showCalories = true }: { macros: Macros; showCalories?: boolean }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5 text-xs">
      {showCalories && (
        <span className="rounded-full bg-slate-100 px-2 py-0.5 font-medium text-slate-700">
          {macros.calories} kcal
        </span>
      )}
      <span className="rounded-full bg-indigo-50 px-2 py-0.5 font-medium text-indigo-700">
        P {macros.protein_g}g
      </span>
      <span className="rounded-full bg-emerald-50 px-2 py-0.5 font-medium text-emerald-700">
        C {macros.carbs_g}g
      </span>
      <span className="rounded-full bg-amber-50 px-2 py-0.5 font-medium text-amber-700">
        F {macros.fat_g}g
      </span>
    </div>
  );
}

function Caret({ open }: { open: boolean }) {
  return (
    <span
      className={`grid h-6 w-6 shrink-0 place-items-center rounded-md transition ${
        open ? "bg-indigo-100 text-indigo-600" : "bg-slate-100 text-slate-500"
      }`}
      aria-hidden
    >
      <svg
        viewBox="0 0 24 24"
        className={`h-4 w-4 transition-transform duration-200 ${open ? "rotate-90" : ""}`}
        fill="none"
        stroke="currentColor"
        strokeWidth={2.5}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 6l6 6-6 6" />
      </svg>
    </span>
  );
}

function MealDraftEditor({
  items,
  onChange,
  onDiscard,
}: {
  items: string[];
  onChange: (items: string[]) => void;
  onDiscard: () => void;
}) {
  return (
    <div className="space-y-2 border-t border-indigo-100 bg-indigo-50/50 px-3 py-3 sm:px-4">
      <p className="text-xs text-slate-600">
        List the foods you&apos;d like. Your coach will set the portions and nutrition.
      </p>
      {items.map((item, index) => (
        <div key={index} className="flex gap-2">
          <input
            className="input bg-white"
            value={item}
            maxLength={80}
            placeholder="e.g. Masala dosa"
            aria-label={`Food ${index + 1}`}
            onChange={(e) => onChange(items.map((v, i) => (i === index ? e.target.value : v)))}
          />
          <button
            type="button"
            className="btn-secondary shrink-0 px-3"
            aria-label={`Remove food ${index + 1}`}
            disabled={items.length === 1}
            onClick={() => onChange(items.filter((_, i) => i !== index))}
          >
            ×
          </button>
        </div>
      ))}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
        <button
          type="button"
          className="btn-soft btn-sm"
          disabled={items.length >= MAX_FOODS_PER_MEAL}
          onClick={() => onChange([...items, ""])}
        >
          + Add food
        </button>
        <button type="button" className="btn-secondary btn-sm" onClick={onDiscard}>
          Undo changes
        </button>
      </div>
    </div>
  );
}

function SessionRow({
  day,
  session,
  edit,
  onManageMeal,
}: {
  day: string;
  session: DietSession;
  edit?: MealEditing;
  onManageMeal?: ManageMeal;
}) {
  const [open, setOpen] = useState(false);
  const key = mealKey(day, session.name);
  const draft = edit?.drafts[key];

  return (
    <div className={`rounded-xl border ${draft ? "border-indigo-300" : "border-slate-200"}`}>
      <div className="flex items-center">
        <button
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          className="flex min-w-0 flex-1 flex-wrap items-center justify-between gap-2 px-3 py-3 text-left hover:bg-slate-50 sm:px-4"
        >
          <span className="flex min-w-0 flex-wrap items-center gap-x-2">
            <Caret open={open || !!draft} />
            <span className="font-medium text-slate-800">{session.name}</span>
            <span className="text-sm text-slate-500">· {session.option}</span>
          </span>
          <MacroChips macros={session.totals} />
        </button>
        {edit && !draft && (
          <button
            type="button"
            onClick={() => edit.setDraft(key, session.items.map((item) => item.name))}
            className="mr-2 shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium text-indigo-600 hover:bg-indigo-50"
          >
            Edit
          </button>
        )}
        {onManageMeal && (
          <button
            type="button"
            onClick={() => onManageMeal(day, session)}
            className="mr-2 inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-sm font-semibold text-indigo-700 shadow-sm transition hover:border-indigo-600 hover:bg-indigo-600 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 sm:mr-3"
            aria-label={`Edit or delete ${day} ${session.name}`}
          >
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 3.5a2.1 2.1 0 013 3L7 19l-4 1 1-4 12.5-12.5z" />
            </svg>
            <span className="hidden sm:inline">Edit meal</span>
          </button>
        )}
      </div>

      {draft && edit && (
        <MealDraftEditor
          items={draft}
          onChange={(items) => edit.setDraft(key, items)}
          onDiscard={() => edit.setDraft(key, null)}
        />
      )}

      {open && !draft && (
        <div className="border-t border-slate-100 px-3 py-3 sm:px-4">
          <ul className="divide-y divide-slate-100 sm:hidden">
            {session.items.map((item) => (
              <li key={item.name} className="space-y-1.5 py-2 text-sm">
                <div className="flex justify-between gap-3">
                  <span className="min-w-0 text-slate-700">{item.name}</span>
                  <span className="shrink-0 text-slate-500">{item.quantity}</span>
                </div>
                <MacroChips macros={item} />
              </li>
            ))}
          </ul>
          <table className="hidden w-full text-sm sm:table">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="pb-2 font-medium">Item</th>
                <th className="pb-2 font-medium">Qty</th>
                <th className="pb-2 text-right font-medium">Kcal</th>
                <th className="pb-2 text-right font-medium">P</th>
                <th className="pb-2 text-right font-medium">C</th>
                <th className="pb-2 text-right font-medium">F</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {session.items.map((item) => (
                <tr key={item.name}>
                  <td className="py-2 text-slate-700">{item.name}</td>
                  <td className="py-2 text-slate-500">{item.quantity}</td>
                  <td className="py-2 text-right text-slate-600">{item.calories}</td>
                  <td className="py-2 text-right text-indigo-600">{item.protein_g}g</td>
                  <td className="py-2 text-right text-emerald-600">{item.carbs_g}g</td>
                  <td className="py-2 text-right text-amber-600">{item.fat_g}g</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function DayRow({
  day,
  defaultOpen,
  edit,
  onManageMeal,
}: {
  day: DietDay;
  defaultOpen: boolean;
  edit?: MealEditing;
  onManageMeal?: ManageMeal;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const edited = edit
    ? day.sessions.filter((s) => edit.drafts[mealKey(day.day, s.name)]).length
    : 0;

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full flex-wrap items-center justify-between gap-2 bg-slate-50 px-3 py-3 text-left hover:bg-slate-100 sm:px-4"
      >
        <span className="flex items-center gap-2">
          <Caret open={open} />
          <span className="font-semibold text-slate-900">{day.day}</span>
          {edited > 0 && (
            <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700">
              {edited} edited
            </span>
          )}
        </span>
        <MacroChips macros={day.totals} />
      </button>

      {open && (
        <div className="space-y-2 p-2 sm:p-3">
          {day.sessions.map((session) => (
            <SessionRow
              key={session.name}
              day={day.day}
              session={session}
              edit={edit}
              onManageMeal={onManageMeal}
            />
          ))}
          {day.sessions.length === 0 && (
            <p className="px-2 py-3 text-sm text-slate-500">No meals planned for this day.</p>
          )}
        </div>
      )}
    </div>
  );
}

export default function WeeklyDietPlan({
  content,
  edit,
  onManageMeal,
}: {
  content: WeeklyDietContent;
  edit?: MealEditing;
  /** Coach-only: opens the editor for one meal. */
  onManageMeal?: ManageMeal;
}) {
  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl bg-indigo-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">
            Weekly total
          </p>
          <div className="mt-2">
            <MacroChips macros={content.weekly_totals} />
          </div>
        </div>
        <div className="rounded-xl bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
            Daily average
          </p>
          <div className="mt-2">
            <MacroChips macros={content.daily_average} />
          </div>
        </div>
      </div>

      <div className="space-y-2">
        {content.days.map((day, index) => (
          <DayRow
            key={day.day}
            day={day}
            defaultOpen={index === 0}
            edit={edit}
            onManageMeal={onManageMeal}
          />
        ))}
      </div>
    </div>
  );
}
