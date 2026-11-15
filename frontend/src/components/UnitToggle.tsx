import { useState } from "react";
import { useAuth, type UnitSystem, type User } from "../context/AuthContext";
import { api } from "../lib/api";
import { useUnitSystem } from "../lib/units";

const OPTIONS: { value: UnitSystem; label: string }[] = [
  { value: "metric", label: "Metric (kg, cm)" },
  { value: "imperial", label: "Imperial (lb, ft/in)" },
];

/** Saves the metric/imperial preference on the account (FR-2.12). */
export default function UnitToggle() {
  const { setUser } = useAuth();
  const system = useUnitSystem();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const choose = async (value: UnitSystem) => {
    if (value === system || saving) return;
    setSaving(true);
    setError("");
    try {
      setUser(await api.put<User>("/auth/me/preferences", { unit_system: value }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not change units");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div
        role="radiogroup"
        aria-label="Units"
        className="inline-flex rounded-lg border border-slate-300 bg-white p-0.5"
      >
        {OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={system === option.value}
            disabled={saving}
            onClick={() => choose(option.value)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
              system === option.value
                ? "bg-indigo-600 text-white"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  );
}
