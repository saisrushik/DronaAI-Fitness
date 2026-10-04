import { useEffect, useRef, useState } from "react";
import { formatValue } from "../lib/measurements";
import { formatDateTime } from "../lib/requests";

export interface ChartPoint {
  t: number;
  v: number;
}

export interface ChartSeries {
  key: string;
  label: string;
  unit: string;
  color: string;
  points: ChartPoint[];
}

interface Props {
  series: ChartSeries[];
  height?: number;
  ariaLabel: string;
}

const PAD = { top: 16, right: 16, bottom: 30, left: 44 };
const DAY = 24 * 60 * 60 * 1000;

function niceTicks(min: number, max: number, count = 4): number[] {
  const step = (max - min) / count;
  return Array.from({ length: count + 1 }, (_, i) => min + step * i);
}

const shortDate = (t: number) =>
  new Date(t).toLocaleDateString(undefined, { day: "numeric", month: "short" });

/** Time-series line chart with a dot per entry; hovering or focusing a dot shows its value. */
export default function LineChart({ series, height = 240, ariaLabel }: Props) {
  const wrapper = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(600);
  const [active, setActive] = useState<{ series: ChartSeries; point: ChartPoint } | null>(null);
  const hasData = series.some((s) => s.points.length > 0);

  useEffect(() => {
    const element = wrapper.current;
    if (!element) return;
    setWidth(element.clientWidth);
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(element);
    return () => observer.disconnect();
  }, [hasData]);

  const all = series.flatMap((s) => s.points);
  if (!hasData) {
    return (
      <div
        ref={wrapper}
        className="grid w-full place-items-center rounded-xl bg-slate-50 text-sm text-slate-500"
        style={{ height }}
      >
        No entries yet.
      </div>
    );
  }

  let tMin = Math.min(...all.map((p) => p.t));
  let tMax = Math.max(...all.map((p) => p.t));
  if (tMin === tMax) {
    tMin -= DAY;
    tMax += DAY;
  }
  let vMin = Math.min(...all.map((p) => p.v));
  let vMax = Math.max(...all.map((p) => p.v));
  const spread = vMax - vMin || Math.max(1, vMax * 0.05);
  vMin -= spread * 0.15;
  vMax += spread * 0.15;

  const plotW = Math.max(1, width - PAD.left - PAD.right);
  const plotH = height - PAD.top - PAD.bottom;
  const x = (t: number) => PAD.left + ((t - tMin) / (tMax - tMin)) * plotW;
  const y = (v: number) => PAD.top + (1 - (v - vMin) / (vMax - vMin)) * plotH;

  const yTicks = niceTicks(vMin, vMax);
  const xTickCount = Math.max(2, Math.min(5, Math.floor(plotW / 110)));
  const xTicks = Array.from(
    { length: xTickCount },
    (_, i) => tMin + ((tMax - tMin) * i) / (xTickCount - 1),
  );

  const show = (s: ChartSeries, point: ChartPoint) => setActive({ series: s, point });
  const hide = () => setActive(null);

  const tooltipX = active ? x(active.point.t) : 0;
  const tooltipAlign =
    tooltipX < 90 ? "translate-x-0" : tooltipX > width - 90 ? "-translate-x-full" : "-translate-x-1/2";

  return (
    <div ref={wrapper} className="relative w-full min-w-0 select-none" onMouseLeave={hide}>
      {/* Sized by its container so it can shrink; the observer then redraws at the new width. */}
      <svg
        viewBox={`0 0 ${width} ${height}`}
        height={height}
        role="img"
        aria-label={ariaLabel}
        className="block w-full"
      >
        {yTicks.map((tick) => (
          <g key={tick}>
            <line
              x1={PAD.left}
              x2={width - PAD.right}
              y1={y(tick)}
              y2={y(tick)}
              stroke="#e2e8f0"
              strokeDasharray="4 4"
            />
            <text x={PAD.left - 8} y={y(tick)} textAnchor="end" dominantBaseline="middle" className="fill-slate-400 text-[11px]">
              {formatValue(Math.round(tick * 10) / 10)}
            </text>
          </g>
        ))}
        {xTicks.map((tick, i) => (
          <text
            key={tick}
            x={x(tick)}
            y={height - 8}
            textAnchor={i === 0 ? "start" : i === xTicks.length - 1 ? "end" : "middle"}
            className="fill-slate-400 text-[11px]"
          >
            {shortDate(tick)}
          </text>
        ))}

        {series.map((s) => {
          const sorted = [...s.points].sort((a, b) => a.t - b.t);
          const path = sorted.map((p, i) => `${i ? "L" : "M"}${x(p.t)},${y(p.v)}`).join(" ");
          return (
            <g key={s.key}>
              {sorted.length > 1 && (
                <path d={path} fill="none" stroke={s.color} strokeWidth={2.5} strokeLinejoin="round" strokeLinecap="round" />
              )}
              {sorted.map((p) => {
                const isActive = active?.series.key === s.key && active.point === p;
                return (
                  <g key={`${p.t}-${p.v}`}>
                    <circle
                      cx={x(p.t)}
                      cy={y(p.v)}
                      r={isActive ? 7 : 5}
                      fill="#fff"
                      stroke={s.color}
                      strokeWidth={isActive ? 3 : 2.5}
                      className="transition-all"
                    />
                    {/* Larger invisible target so dots are easy to hover and tap. */}
                    <circle
                      cx={x(p.t)}
                      cy={y(p.v)}
                      r={12}
                      fill="transparent"
                      className="cursor-pointer outline-none"
                      tabIndex={0}
                      aria-label={`${s.label}: ${formatValue(p.v)} ${s.unit} on ${formatDateTime(new Date(p.t).toISOString())}`}
                      onMouseEnter={() => show(s, p)}
                      onFocus={() => show(s, p)}
                      onBlur={hide}
                      onClick={() => show(s, p)}
                    />
                  </g>
                );
              })}
            </g>
          );
        })}
      </svg>

      {active && (
        <div
          className={`pointer-events-none absolute z-10 -translate-y-full whitespace-nowrap rounded-lg bg-slate-900 px-3 py-2 text-xs text-white shadow-lg ${tooltipAlign}`}
          style={{ left: tooltipX, top: y(active.point.v) - 12 }}
          role="status"
        >
          <span className="flex items-center gap-1.5 font-semibold">
            <span className="h-2 w-2 rounded-full" style={{ background: active.series.color }} />
            {active.series.label}: {formatValue(active.point.v)} {active.series.unit}
          </span>
          <span className="mt-0.5 block text-slate-300">
            {formatDateTime(new Date(active.point.t).toISOString())}
          </span>
        </div>
      )}
    </div>
  );
}
