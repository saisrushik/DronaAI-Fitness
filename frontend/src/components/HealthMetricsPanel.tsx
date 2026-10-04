import type { HealthMetrics } from "../context/AuthContext";

function Tile({
  label,
  value,
  sub,
  hint,
}: {
  label: string;
  value: string | number;
  sub?: string;
  hint?: string;
}) {
  return (
    <div className="min-w-0 rounded-xl bg-slate-50 p-4" title={hint}>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 break-words text-xl font-bold text-slate-900 sm:text-2xl">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

export default function HealthMetricsPanel({ metrics }: { metrics: HealthMetrics }) {
  const { bmi, macros, body_fat, healthy_weight, heart_rate } = metrics;

  return (
    <div className="space-y-6">
      <section>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Body composition
        </h3>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Tile
            label="BMI"
            value={bmi.value}
            sub={`WHO: ${bmi.who} · Asian: ${bmi.asian}`}
            hint="weight (kg) / height (m)²"
          />
          <Tile
            label="Body fat"
            value={body_fat ? `${body_fat.value}%` : "—"}
            sub={body_fat ? body_fat.category : "Needs waist & neck measurements"}
            hint="US Navy method"
          />
          <Tile
            label="Lean body mass"
            value={`${metrics.lean_body_mass} kg`}
            hint="Boer formula"
          />
          <Tile label="Ideal weight" value={`${metrics.ideal_weight} kg`} hint="Devine formula" />
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
            hint="Mifflin-St Jeor equation"
          />
          <Tile
            label="TDEE"
            value={`${metrics.tdee} kcal`}
            sub="Including activity"
            hint="BMR × activity multiplier"
          />
          <Tile
            label="Daily target"
            value={`${metrics.target_calories} kcal`}
            sub={metrics.calorie_floor_applied ? "Safety floor applied" : "Adjusted for your goal"}
          />
          <Tile
            label="Macros"
            value={`${macros.protein_g}P`}
            sub={`${macros.carbs_g}g carbs · ${macros.fat_g}g fat`}
          />
        </div>
      </section>

      <section>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Healthy weight range
        </h3>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <Tile
            label="WHO range"
            value={`${healthy_weight.who[0]}–${healthy_weight.who[1]} kg`}
            sub="BMI 18.5–24.9"
          />
          <Tile
            label="Asian range"
            value={`${healthy_weight.asian[0]}–${healthy_weight.asian[1]} kg`}
            sub="BMI 18.5–22.9"
          />
        </div>
      </section>

      <section>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Heart rate zones
        </h3>
        <p className="mt-1 text-sm text-slate-500">
          Max heart rate {heart_rate.max} bpm (Tanaka formula)
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
