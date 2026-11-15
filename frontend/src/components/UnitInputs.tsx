import { useEffect, useState } from "react";
import {
  cmFromFeetAndInches,
  displayBounds,
  feetAndInches,
  formatNumber,
  toDisplay,
  toMetric,
  type Quantity,
  type UnitSystem,
} from "../lib/units";

interface MeasureInputProps {
  id: string;
  quantity: Quantity;
  system: UnitSystem;
  /** Metric value as typed text ("" when empty). */
  value: string;
  onChange: (metric: string) => void;
  /** Metric limits, as validated by the API. */
  min: number;
  max: number;
  required?: boolean;
  placeholder?: string;
}

const metricFromText = (text: string, quantity: Quantity, system: UnitSystem) =>
  text.trim() === "" ? "" : String(toMetric(Number(text), quantity, system));

const textFromMetric = (metric: string, quantity: Quantity, system: UnitSystem) =>
  metric === "" ? "" : formatNumber(toDisplay(Number(metric), quantity, system));

/** Number input shown in the user's unit; reports the value in kg or cm. */
export function MeasureInput({
  id,
  quantity,
  system,
  value,
  onChange,
  min,
  max,
  required = false,
  placeholder,
}: MeasureInputProps) {
  const [text, setText] = useState(() => textFromMetric(value, quantity, system));

  // Re-sync only when the value changed from outside (a reset, or a unit switch), so typing
  // "72." or "180.5" isn't rewritten mid-way.
  useEffect(() => {
    if (metricFromText(text, quantity, system) !== value) {
      setText(textFromMetric(value, quantity, system));
    }
  }, [value, system, quantity]);

  const bounds = displayBounds(min, max, quantity, system);
  return (
    <input
      id={id}
      type="number"
      inputMode="decimal"
      step="0.1"
      min={bounds.min}
      max={bounds.max}
      required={required}
      value={text}
      onChange={(e) => {
        setText(e.target.value);
        onChange(metricFromText(e.target.value, quantity, system));
      }}
      className="input"
      placeholder={placeholder}
    />
  );
}

function splitHeight(metric: string) {
  if (metric === "") return { feet: "", inches: "" };
  const { feet, inches } = feetAndInches(Number(metric));
  return { feet: String(feet), inches: formatNumber(inches) };
}

function joinHeight(feet: string, inches: string): string {
  if (feet.trim() === "" && inches.trim() === "") return "";
  return String(cmFromFeetAndInches(Number(feet || 0), Number(inches || 0)));
}

function FeetInchesInput({
  id,
  value,
  onChange,
  required,
}: {
  id: string;
  value: string;
  onChange: (metric: string) => void;
  required?: boolean;
}) {
  const [parts, setParts] = useState(() => splitHeight(value));

  useEffect(() => {
    if (joinHeight(parts.feet, parts.inches) !== value) setParts(splitHeight(value));
  }, [value]);

  const set = (next: { feet: string; inches: string }) => {
    setParts(next);
    onChange(joinHeight(next.feet, next.inches));
  };

  return (
    <div className="grid grid-cols-2 gap-2">
      <div className="relative">
        <input
          id={id}
          type="number"
          inputMode="numeric"
          min={3}
          max={8}
          step="1"
          required={required}
          aria-label="Feet"
          value={parts.feet}
          onChange={(e) => set({ ...parts, feet: e.target.value })}
          className="input pr-9"
          placeholder="5"
        />
        <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-slate-500">
          ft
        </span>
      </div>
      <div className="relative">
        <input
          type="number"
          inputMode="decimal"
          min={0}
          max={11.9}
          step="0.1"
          aria-label="Inches"
          value={parts.inches}
          onChange={(e) => set({ ...parts, inches: e.target.value })}
          className="input pr-9"
          placeholder="10"
        />
        <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-slate-500">
          in
        </span>
      </div>
    </div>
  );
}

/** Height in cm, or feet and inches for imperial users. Reports centimetres. */
export function HeightInput({
  id,
  system,
  value,
  onChange,
  required = false,
  placeholder,
}: {
  id: string;
  system: UnitSystem;
  value: string;
  onChange: (metric: string) => void;
  required?: boolean;
  placeholder?: string;
}) {
  if (system === "imperial") {
    return <FeetInchesInput id={id} value={value} onChange={onChange} required={required} />;
  }
  return (
    <MeasureInput
      id={id}
      quantity="length"
      system={system}
      value={value}
      onChange={onChange}
      min={100}
      max={250}
      required={required}
      placeholder={placeholder}
    />
  );
}
