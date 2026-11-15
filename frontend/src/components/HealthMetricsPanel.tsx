import { useId } from "react";
import type { HealthMetrics } from "../context/AuthContext";
import { labelFor } from "../lib/profileOptions";
import { formatNumber, formatWeight, toDisplay, unitLabel, useUnitSystem } from "../lib/units";

/** "How this is calculated" (BRD FR-8.1), shown on hover, keyboard focus or tap. */
function InfoTooltip({ label, text }: { label: string; text: string }) {
  const id = useId();
  return (
    <span className="group relative shrink-0">
      <button
        type="button"
        aria-label={`How ${label} is calculated`}
        aria-describedby={id}
        className="grid h-5 w-5 place-items-center rounded-full border border-slate-300 bg-white text-[11px] font-bold text-slate-500 transition hover:border-indigo-500 hover:bg-indigo-600 hover:text-white focus:border-indigo-500 focus:bg-indigo-600 focus:text-white focus:outline-none"
      >
        i
      </button>
      <span
        id={id}
        role="tooltip"
        className="pointer-events-none invisible absolute right-0 top-full z-30 mt-2 w-72 max-w-[80vw] rounded-lg bg-slate-900 p-3 text-xs leading-relaxed text-slate-100 opacity-0 shadow-xl transition duration-150 group-focus-within:visible group-focus-within:opacity-100 group-hover:visible group-hover:opacity-100"
      >
        <span className="mb-1 block font-semibold text-white">How this is calculated</span>
        {text}
      </span>
    </span>
  );
}

function Tile({
  label,
  value,
  sub,
  explain,
}: {
  label: string;
  value: string | number;
  sub?: string;
  explain?: string;
}) {
  return (
    <div className="min-w-0 rounded-xl bg-slate-50 p-4">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
        {explain && <InfoTooltip label={label} text={explain} />}
      </div>
      <p className="mt-1 break-words text-xl font-bold text-slate-900 sm:text-2xl">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

const signed = (value: number) => `${value < 0 ? "−" : "+"} ${Math.abs(value)}`;

/** Plain-language formulas with the customer's own numbers plugged in. Formulas use kg and cm. */
function explanations(metrics: HealthMetrics) {
  const { inputs: i, calorie_breakdown: c } = metrics;
  const female = i.gender === "female";
  const metres = (i.height_cm / 100).toFixed(2);
  const inchesOver = Math.max(0, i.height_cm / 2.54 - 60).toFixed(1);

  const bodyFat = !metrics.body_fat
    ? `US Navy method. It needs your waist and neck${female ? ", plus hip," : ""} measurements.`
    : female
      ? `US Navy method: 495 ÷ (1.29579 − 0.35004 × log₁₀(waist + hip − neck) + 0.22100 × log₁₀(height)) − 450, using waist ${i.waist_cm} cm, hip ${i.hip_cm} cm, neck ${i.neck_cm} cm and height ${i.height_cm} cm.`
      : `US Navy method: 495 ÷ (1.0324 − 0.19077 × log₁₀(waist − neck) + 0.15456 × log₁₀(height)) − 450, using waist ${i.waist_cm} cm, neck ${i.neck_cm} cm and height ${i.height_cm} cm.`;

  return {
    bmi:
      `Weight ÷ height²: ${i.weight_kg} kg ÷ (${metres} m)² = ${metrics.bmi.value}. ` +
      "Asian cut-offs are lower than WHO's (normal is 18.5–22.9 instead of 18.5–24.9) because " +
      "health risks rise at a lower BMI for South Asians.",
    bodyFat,
    lbm: female
      ? `Boer formula: 0.252 × ${i.weight_kg} kg + 0.473 × ${i.height_cm} cm − 48.3 = ${metrics.lean_body_mass} kg.`
      : `Boer formula: 0.407 × ${i.weight_kg} kg + 0.267 × ${i.height_cm} cm − 19.2 = ${metrics.lean_body_mass} kg.`,
    ideal:
      `Devine formula: ${female ? "45.5" : "50"} kg + 2.3 kg for every inch over 5 ft ` +
      `(${inchesOver} in) = ${metrics.ideal_weight} kg.`,
    bmr:
      `Mifflin-St Jeor equation: 10 × ${i.weight_kg} kg + 6.25 × ${i.height_cm} cm − 5 × ${i.age} ` +
      `years ${i.gender === "male" ? "+ 5" : "− 161"} = ${metrics.bmr} kcal burned at complete rest.`,
    tdee:
      `BMR × activity multiplier: ${metrics.bmr} × ${i.activity_multiplier} ` +
      `(${labelFor("activity", i.activity_level)}) = ${metrics.tdee} kcal.`,
    target:
      `TDEE ${c.tdee} ${signed(c.goal_delta)} kcal for ${labelFor("goal", i.goal)}` +
      (c.coach_adjustment
        ? ` ${signed(c.coach_adjustment)} kcal from your coach's weekly reviews`
        : "") +
      ` = ${c.target} kcal. It never goes below the ${c.floor} kcal safety floor.`,
    macros:
      `Protein: ${i.protein_per_kg} g per kg × ${i.weight_kg} kg. Fat: ${Math.round(i.fat_share * 100)}% ` +
      "of calories, and at least 0.8 g per kg. Carbs: whatever calories remain, at 4 kcal per gram.",
    healthy:
      "The weights that give a normal BMI at your height: 18.5–24.9 (WHO) or 18.5–22.9 " +
      `(Asian) × (${metres} m)².`,
    heartRate:
      `Tanaka formula: 208 − 0.7 × ${i.age} years = ${metrics.heart_rate.max} bpm. Each zone is a ` +
      "percentage of that maximum.",
  };
}

export default function HealthMetricsPanel({ metrics }: { metrics: HealthMetrics }) {
  const system = useUnitSystem();
  const { bmi, macros, body_fat, healthy_weight, heart_rate } = metrics;
  const explain = explanations(metrics);
  // BRD 5.1: Indian users see the Asian cut-offs first; both standards are always shown.
  const asianFirst = bmi.primary === "asian";
  const bmiSub = asianFirst
    ? `Asian: ${bmi.asian} · WHO: ${bmi.who}`
    : `WHO: ${bmi.who} · Asian: ${bmi.asian}`;
  const range = ([low, high]: [number, number]) =>
    `${formatNumber(toDisplay(low, "weight", system))}–${formatNumber(
      toDisplay(high, "weight", system),
    )} ${unitLabel("weight", system)}`;
  const ranges = [
    { label: "WHO range", value: range(healthy_weight.who), sub: "BMI 18.5–24.9" },
    { label: "Asian range", value: range(healthy_weight.asian), sub: "BMI 18.5–22.9" },
  ];
  if (asianFirst) ranges.reverse();

  return (
    <div className="space-y-6">
      <section>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Body composition
        </h3>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Tile label="BMI" value={bmi.value} sub={bmiSub} explain={explain.bmi} />
          <Tile
            label="Body fat"
            value={body_fat ? `${body_fat.value}%` : "—"}
            sub={body_fat ? body_fat.category : "Needs waist & neck measurements"}
            explain={explain.bodyFat}
          />
          <Tile
            label="Lean body mass"
            value={formatWeight(metrics.lean_body_mass, system)}
            explain={explain.lbm}
          />
          <Tile
            label="Ideal weight"
            value={formatWeight(metrics.ideal_weight, system)}
            explain={explain.ideal}
          />
        </div>
      </section>

      <section>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Energy & macros
        </h3>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Tile
            label="BMR"
            value={`${metrics.bmr} kcal`}
            sub="At complete rest"
            explain={explain.bmr}
          />
          <Tile
            label="TDEE"
            value={`${metrics.tdee} kcal`}
            sub="Including activity"
            explain={explain.tdee}
          />
          <Tile
            label="Daily target"
            value={`${metrics.target_calories} kcal`}
            sub={
              metrics.calorie_floor_applied
                ? "Safety floor applied"
                : metrics.calorie_breakdown.coach_adjustment
                  ? "Adjusted for your goal and by your coach"
                  : "Adjusted for your goal"
            }
            explain={explain.target}
          />
          <Tile
            label="Macros"
            value={`${macros.protein_g}g protein`}
            sub={`${macros.carbs_g}g carbs · ${macros.fat_g}g fat`}
            explain={explain.macros}
          />
        </div>
      </section>

      <section>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Healthy weight range
        </h3>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {ranges.map(({ label, value, sub }) => (
            <Tile key={label} label={label} value={value} sub={sub} explain={explain.healthy} />
          ))}
        </div>
      </section>

      <section>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Heart rate zones
        </h3>
        <p className="mt-1 text-sm text-slate-500">
          Max heart rate {heart_rate.max} bpm. {explain.heartRate}
        </p>
        <table className="mt-3 w-full text-sm">
          <tbody className="divide-y divide-slate-100">
            {heart_rate.zones.map((zone) => (
              <tr key={zone.name}>
                <td className="py-2 text-slate-700">{zone.name}</td>
                <td className="py-2 text-right font-medium text-slate-900">
                  {zone.low}–{zone.high} bpm
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
