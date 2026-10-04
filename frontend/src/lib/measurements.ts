export interface Measurement {
  id: string;
  recorded_at: string;
  weight_kg: number | null;
  height_cm: number | null;
  waist_cm: number | null;
  neck_cm: number | null;
  hip_cm: number | null;
}

export type MetricKey = "weight_kg" | "height_cm" | "waist_cm" | "neck_cm" | "hip_cm";

export interface MetricConfig {
  key: MetricKey;
  label: string;
  unit: string;
  color: string;
  min: number;
  max: number;
}

// Ranges mirror the API's validation.
export const METRICS: MetricConfig[] = [
  { key: "weight_kg", label: "Weight", unit: "kg", color: "#6366f1", min: 30, max: 250 },
  { key: "height_cm", label: "Height", unit: "cm", color: "#10b981", min: 100, max: 250 },
  { key: "waist_cm", label: "Waist", unit: "cm", color: "#f59e0b", min: 40, max: 200 },
  { key: "neck_cm", label: "Neck", unit: "cm", color: "#f43f5e", min: 20, max: 60 },
  { key: "hip_cm", label: "Hip", unit: "cm", color: "#0ea5e9", min: 40, max: 200 },
];

export const formatValue = (value: number) =>
  Number.isInteger(value) ? String(value) : value.toFixed(1);
