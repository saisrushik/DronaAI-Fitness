import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth, type User } from "../context/AuthContext";
import { api } from "../lib/api";
import { METRICS, type MetricKey } from "../lib/measurements";

const emptyValues = (): Record<MetricKey, string> => ({
  weight_kg: "",
  height_cm: "",
  waist_cm: "",
  neck_cm: "",
  hip_cm: "",
});

/** "YYYY-MM-DDTHH:mm" in local time, as datetime-local inputs expect. */
function localNow(): string {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}

export default function MeasurementLogCard() {
  const { user, setUser } = useAuth();
  const [values, setValues] = useState(emptyValues);
  const [when, setWhen] = useState(localNow);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const section = useRef<HTMLElement>(null);
  const { hash } = useLocation();

  useEffect(() => {
    if (hash === "#log-measurements") {
      section.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [hash]);

  const filled = METRICS.filter((metric) => values[metric.key].trim() !== "");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setSaved(false);
    setSaving(true);
    try {
      const body: Record<string, number | string> = { recorded_at: new Date(when).toISOString() };
      for (const metric of filled) body[metric.key] = Number(values[metric.key]);
      await api.post("/measurements", body);
      // Logging can change the profile's current values, which drive the health metrics.
      setUser(await api.get<User>("/auth/me"));
      setValues(emptyValues());
      setWhen(localNow());
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not log your measurements");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section ref={section} id="log-measurements" className="card scroll-mt-24">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-xl font-semibold">Log body measurements</h2>
          <p className="mt-1 text-sm text-slate-600">
            Record any measurements you&apos;ve taken. Leave the rest blank.
          </p>
        </div>
        <Link to="/monitoring" className="btn-soft">
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 17l6-6 4 4 8-8M14 7h7v7" />
          </svg>
          View trends
        </Link>
      </div>

      <form onSubmit={submit} className="mt-4 space-y-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {METRICS.map((metric) => {
            const current = user?.customer?.[metric.key];
            return (
              <div key={metric.key}>
                <label className="label flex items-center gap-1.5" htmlFor={`log-${metric.key}`}>
                  <span className="h-2 w-2 rounded-full" style={{ background: metric.color }} />
                  {metric.label} ({metric.unit})
                </label>
                <input
                  id={`log-${metric.key}`}
                  type="number"
                  inputMode="decimal"
                  step="0.1"
                  min={metric.min}
                  max={metric.max}
                  value={values[metric.key]}
                  onChange={(e) => setValues({ ...values, [metric.key]: e.target.value })}
                  className="input"
                  placeholder={current ? `Now ${current}` : ""}
                />
              </div>
            );
          })}
          <div className="col-span-2 sm:col-span-1">
            <label className="label" htmlFor="log-when">
              Measured on
            </label>
            <input
              id="log-when"
              type="datetime-local"
              required
              max={localNow()}
              value={when}
              onChange={(e) => setWhen(e.target.value)}
              className="input"
            />
          </div>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex flex-wrap items-center gap-3">
          <button type="submit" className="btn-primary" disabled={saving || filled.length === 0}>
            {saving ? "Saving…" : "Log measurements"}
          </button>
          {saved && <span className="text-sm text-emerald-600">Measurements logged.</span>}
        </div>
      </form>
    </section>
  );
}
