import { MAX_FOODS_PER_MEAL, MacroChips, type DietItem } from "./WeeklyDietPlan";

const NUTRIENTS = [
  { field: "calories", label: "Kcal", max: 5000 },
  { field: "protein_g", label: "Protein (g)", max: 500 },
  { field: "carbs_g", label: "Carbs (g)", max: 500 },
  { field: "fat_g", label: "Fat (g)", max: 500 },
] as const;

/** Form state for one food; numbers stay strings while being typed. */
export interface ItemDraft {
  name: string;
  quantity: string;
  calories: string;
  protein_g: string;
  carbs_g: string;
  fat_g: string;
}

export const blankItem = (name = ""): ItemDraft => ({
  name,
  quantity: "",
  calories: "",
  protein_g: "",
  carbs_g: "",
  fat_g: "",
});

export const draftFromItem = (item: DietItem): ItemDraft => ({
  name: item.name,
  quantity: item.quantity,
  calories: String(item.calories),
  protein_g: String(item.protein_g),
  carbs_g: String(item.carbs_g),
  fat_g: String(item.fat_g),
});

export const itemFromDraft = (item: ItemDraft): DietItem => ({
  name: item.name.trim(),
  quantity: item.quantity.trim(),
  calories: Number(item.calories),
  protein_g: Number(item.protein_g),
  carbs_g: Number(item.carbs_g),
  fat_g: Number(item.fat_g),
});

export const draftTotals = (items: ItemDraft[]) => {
  const sum = (field: (typeof NUTRIENTS)[number]["field"]) =>
    Math.round(items.reduce((total, item) => total + (Number(item[field]) || 0), 0));
  return {
    calories: sum("calories"),
    protein_g: sum("protein_g"),
    carbs_g: sum("carbs_g"),
    fat_g: sum("fat_g"),
  };
};

interface Props {
  items: ItemDraft[];
  onChange: (items: ItemDraft[]) => void;
  /** Unique prefix for input ids. */
  idPrefix: string;
  minItems?: number;
}

/** Editable list of foods with quantity, calories and macros. */
export default function NutritionItemsEditor({ items, onChange, idPrefix, minItems = 1 }: Props) {
  return (
    <div className="space-y-3">
      {items.map((item, index) => {
        const setField = (field: keyof ItemDraft, value: string) =>
          onChange(items.map((it, i) => (i === index ? { ...it, [field]: value } : it)));
        const id = `${idPrefix}-${index}`;
        return (
          <div key={index} className="space-y-2 rounded-lg bg-slate-50 p-3">
            <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_10rem_auto] sm:items-end">
              <div>
                <label className="text-xs font-medium text-slate-600" htmlFor={`${id}-name`}>
                  Food
                </label>
                <input
                  id={`${id}-name`}
                  className="input bg-white"
                  required
                  maxLength={80}
                  value={item.name}
                  onChange={(e) => setField("name", e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600" htmlFor={`${id}-qty`}>
                  Quantity
                </label>
                <input
                  id={`${id}-qty`}
                  className="input bg-white"
                  required
                  maxLength={40}
                  placeholder="e.g. 150 g"
                  value={item.quantity}
                  onChange={(e) => setField("quantity", e.target.value)}
                />
              </div>
              <button
                type="button"
                className="btn-secondary"
                disabled={items.length <= minItems}
                onClick={() => onChange(items.filter((_, i) => i !== index))}
              >
                Remove
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {NUTRIENTS.map(({ field, label, max }) => (
                <div key={field}>
                  <label className="text-xs font-medium text-slate-600" htmlFor={`${id}-${field}`}>
                    {label}
                  </label>
                  <input
                    id={`${id}-${field}`}
                    className="input bg-white"
                    type="number"
                    inputMode="decimal"
                    min={0}
                    max={max}
                    step="0.1"
                    required
                    value={item[field]}
                    onChange={(e) => setField(field, e.target.value)}
                  />
                </div>
              ))}
            </div>
          </div>
        );
      })}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <button
          type="button"
          className="btn-soft btn-sm"
          disabled={items.length >= MAX_FOODS_PER_MEAL}
          onClick={() => onChange([...items, blankItem()])}
        >
          + Add food
        </button>
        {items.length > 0 && <MacroChips macros={draftTotals(items)} />}
      </div>
    </div>
  );
}
