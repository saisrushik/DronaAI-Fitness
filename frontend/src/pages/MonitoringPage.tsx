import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import LineChart, { type ChartSeries } from "../components/LineChart";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import {
  METRICS,
  formatValue,
  type Measurement,
  type MetricConfig,
  type MetricKey,
} from "../lib/measurements";
import { formatDateTime } from "../lib/requests";

function toSeries(metric: MetricConfig, entries: Measurement[]): ChartSeries {
  return {
    key: metric.key,
    label: metric.label,
    unit: metric.unit,
    color: metric.color,
    points: entries
      .filter((entry) => entry[metric.key] !== null)
      .map((entry) => ({ t: Date.parse(entry.recorded_at), v: entry[metric.key] as number })),
  };
}

function Swatch({ color }: { color: string }) {
  return <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: color }} />;
}

function SummaryTile({ metric, series }: { metric: MetricConfig; series: ChartSeries }) {
  const points = series.points;
  const latest = points.at(-1);
  const change = points.length > 1 ? points[points.length - 1].v - points[0].v : null;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        <Swatch color={metric.color} />
        {metric.label}
      </p>
      <p className="mt-1 text-2xl font-bold text-slate-900">
        {latest ? `${formatValue(latest.v)} ${metric.unit}` : "—"}
      </p>
      <p className="mt-0.5 text-xs text-slate-500">
        {change === null
          ? `${points.length} entr${points.length === 1 ? "y" : "ies"}`
          : `${change > 0 ? "▲ +" : change < 0 ? "▼ " : ""}${formatValue(Math.round(change * 10) / 10)} ${metric.unit} since first log`}
      </p>
    </div>
  );
}

export default function MonitoringPage() {
  const { user } = useAuth();
  const [entries, setEntries] = useState<Measurement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [hidden, setHidden] = useState<Set<MetricKey>>(new Set());

  useEffect(() => {
    if (user?.role !== "customer") return;
    api
      .get<Measurement[]>("/measurements")
      .then(setEntries)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load measurements"))
      .finally(() => setLoading(false));
  }, [user?.role]);

  const series = useMemo(
    () => METRICS.map((metric) => ({ metric, series: toSeries(metric, entries) })),
    [entries],
  );
  const tracked = series.filter(({ series: s }) => s.points.length > 0);

  const toggle = (key: MetricKey) =>
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  if (user?.role !== "customer") {
    return <p className="py-20 text-center text-slate-500">This page is for customers.</p>;
  }
  if (loading) return <p className="py-20 text-center text-slate-500">Loading measurements…</p>;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold sm:text-3xl">Personal monitoring</h1>
          <p className="mt-1 text-slate-600">
            How your body measurements have changed over time. Hover or tap a dot to see the
            exact value.
          </p>
        </div>
        <Link to="/profile#log-measurements" className="btn-primary w-full sm:w-auto">
          + Log measurements
        </Link>
      </header>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {entries.length === 0 ? (
        <div className="card text-center">
          <h2 className="font-semibold">No measurements yet</h2>
          <p className="mt-2 text-sm text-slate-600">
            Log your weight, height, waist, neck and hip on your profile to start seeing trends
            here.
          </p>
          <Link to="/profile#log-measurements" className="btn-primary mx-auto mt-4">
            Log measurements
          </Link>
        </div>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {series.map(({ metric, series: s }) => (
              <SummaryTile key={metric.key} metric={metric} series={s} />
            ))}
          </div>

          <section className="card">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-semibold">All measurements</h2>
              <div className="flex flex-wrap gap-2" role="group" aria-label="Show or hide metrics">
                {tracked.map(({ metric }) => {
                  const on = !hidden.has(metric.key);
                  return (
                    <button
                      key={metric.key}
                      type="button"
                      onClick={() => toggle(metric.key)}
                      aria-pressed={on}
                      className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition ${
                        on
                          ? "border-slate-300 bg-white text-slate-800"
                          : "border-slate-200 bg-slate-50 text-slate-400 line-through"
                      }`}
                    >
                      <Swatch color={on ? metric.color : "#cbd5e1"} />
                      {metric.label}
                    </button>
                  );
                })}
              </div>
            </div>
            <div className="mt-4">
              <LineChart
                ariaLabel="All body measurements over time"
                height={280}
                series={tracked
                  .filter(({ metric }) => !hidden.has(metric.key))
                  .map(({ series: s }) => s)}
              />
            </div>
          </section>

          <div className="grid gap-4 md:grid-cols-2">
            {tracked.map(({ metric, series: s }) => (
              <section key={metric.key} className="card">
                <h3 className="flex items-center gap-2 font-semibold">
                  <Swatch color={metric.color} />
                  {metric.label} <span className="font-normal text-slate-500">({metric.unit})</span>
                </h3>
                <div className="mt-3">
                  <LineChart ariaLabel={`${metric.label} over time`} height={200} series={[s]} />
                </div>
              </section>
            ))}
          </div>

          <section className="card">
            <h2 className="text-lg font-semibold">History</h2>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[34rem] text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
                    <th className="py-2 pr-4 font-medium">Logged</th>
                    {METRICS.map((metric) => (
                      <th key={metric.key} className="py-2 pr-4 text-right font-medium">
                        {metric.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {[...entries].reverse().map((entry) => (
                    <tr key={entry.id}>
                      <td className="whitespace-nowrap py-2 pr-4 text-slate-600">
                        {formatDateTime(entry.recorded_at)}
                      </td>
                      {METRICS.map((metric) => (
                        <td key={metric.key} className="whitespace-nowrap py-2 pr-4 text-right text-slate-800">
                          {entry[metric.key] !== null
                            ? `${formatValue(entry[metric.key] as number)} ${metric.unit}`
                            : <span className="text-slate-300">—</span>}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
