/** Metric/imperial display (FR-2.12). Everything is stored and calculated in kg and cm. */
import { useAuth, type UnitSystem } from "../context/AuthContext";

export type { UnitSystem };
/** Body weight, or a length such as height or a circumference. */
export type Quantity = "weight" | "length";

const KG_PER_LB = 0.45359237;
const CM_PER_IN = 2.54;

const round1 = (value: number) => Math.round(value * 10) / 10;

export const formatNumber = (value: number) =>
  Number.isInteger(value) ? String(value) : value.toFixed(1);

export function useUnitSystem(): UnitSystem {
  return useAuth().user?.unit_system ?? "metric";
}

export function unitLabel(quantity: Quantity, system: UnitSystem): string {
  if (quantity === "weight") return system === "imperial" ? "lb" : "kg";
  return system === "imperial" ? "in" : "cm";
}

/** Metric value -> the user's unit, to one decimal place. */
export function toDisplay(metric: number, quantity: Quantity, system: UnitSystem): number {
  if (system === "metric") return round1(metric);
  return round1(quantity === "weight" ? metric / KG_PER_LB : metric / CM_PER_IN);
}

/** User's unit -> metric, to one decimal place (the precision the API stores). */
export function toMetric(display: number, quantity: Quantity, system: UnitSystem): number {
  if (system === "metric") return round1(display);
  return round1(quantity === "weight" ? display * KG_PER_LB : display * CM_PER_IN);
}

/** Converts metric validation limits into the user's unit, staying inside them. */
export function displayBounds(min: number, max: number, quantity: Quantity, system: UnitSystem) {
  if (system === "metric") return { min, max };
  const factor = quantity === "weight" ? 1 / KG_PER_LB : 1 / CM_PER_IN;
  return { min: Math.ceil(min * factor * 10) / 10, max: Math.floor(max * factor * 10) / 10 };
}

export function format(
  metric: number | null | undefined,
  quantity: Quantity,
  system: UnitSystem,
): string {
  if (metric === null || metric === undefined) return "—";
  return `${formatNumber(toDisplay(metric, quantity, system))} ${unitLabel(quantity, system)}`;
}

export const formatWeight = (kg: number | null | undefined, system: UnitSystem) =>
  format(kg, "weight", system);

export const formatLength = (cm: number | null | undefined, system: UnitSystem) =>
  format(cm, "length", system);

/** Height reads more naturally as feet and inches than as a single inch figure. */
export function formatHeight(cm: number | null | undefined, system: UnitSystem): string {
  if (cm === null || cm === undefined) return "—";
  if (system === "metric") return `${formatNumber(round1(cm))} cm`;
  const { feet, inches } = feetAndInches(cm);
  return `${feet}′ ${formatNumber(inches)}″`;
}

export function feetAndInches(cm: number): { feet: number; inches: number } {
  const total = cm / CM_PER_IN;
  let feet = Math.floor(total / 12);
  let inches = round1(total - feet * 12);
  if (inches >= 12) {
    feet += 1;
    inches = 0;
  }
  return { feet, inches };
}

export const cmFromFeetAndInches = (feet: number, inches: number) =>
  round1((feet * 12 + inches) * CM_PER_IN);

/** A signed change such as "-0.4 kg", for trends. */
export function formatChange(kg: number, system: UnitSystem): string {
  const value = toDisplay(kg, "weight", system);
  return `${value > 0 ? "+" : ""}${formatNumber(value)} ${unitLabel("weight", system)}`;
}
