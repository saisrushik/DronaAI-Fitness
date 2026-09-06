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
      className={`inline-block text-slate-400 transition-transform ${open ? "rotate-90" : ""}`}
      aria-hidden
    >
      ▶
    </span>
  );
}

function SessionRow({ session }: { session: DietSession }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-xl border border-slate-200">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full flex-wrap items-center justify-between gap-2 px-4 py-3 text-left hover:bg-slate-50"
      >
        <span className="flex items-center gap-2">
          <Caret open={open} />
          <span className="font-medium text-slate-800">{session.name}</span>
          <span className="text-sm text-slate-500">· {session.option}</span>
        </span>
        <MacroChips macros={session.totals} />
      </button>

      {open && (
        <div className="border-t border-slate-100 px-4 py-3">
          <table className="w-full text-sm">
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

function DayRow({ day, defaultOpen }: { day: DietDay; defaultOpen: boolean }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full flex-wrap items-center justify-between gap-2 bg-slate-50 px-4 py-3 text-left hover:bg-slate-100"
      >
        <span className="flex items-center gap-2">
          <Caret open={open} />
          <span className="font-semibold text-slate-900">{day.day}</span>
        </span>
        <MacroChips macros={day.totals} />
      </button>

      {open && (
        <div className="space-y-2 p-3">
          {day.sessions.map((session) => (
            <SessionRow key={session.name} session={session} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function WeeklyDietPlan({ content }: { content: WeeklyDietContent }) {
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
          <DayRow key={day.day} day={day} defaultOpen={index === 0} />
        ))}
      </div>
    </div>
  );
}
