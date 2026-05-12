import { useMemo } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { InventoryPayload, Point, UnitChoice } from "../types";
import { convert, fmtDate, fmtValue } from "../format";

// Merge current + overlays into a single array keyed by date (string).
// Overlays (avg/max/min) are aligned to the current calendar year, so we
// also project them onto the calendar of `current` by ISO week so the
// chart shows them along the entire current line.
type Row = {
  date: string;
  current?: number | null;
  avg?: number | null;
  min?: number | null;
  max?: number | null;
  bandLow?: number | null;
  bandHigh?: number | null;
};

function isoWeek(d: Date): number {
  // ISO week per https://stackoverflow.com/a/6117889 (UTC-safe).
  const target = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
  const dayNr = (target.getUTCDay() + 6) % 7;
  target.setUTCDate(target.getUTCDate() - dayNr + 3);
  const firstThursday = new Date(Date.UTC(target.getUTCFullYear(), 0, 4));
  const diff = (target.getTime() - firstThursday.getTime()) / 86400000;
  return 1 + Math.floor(diff / 7);
}

function indexByWeek(points: Point[]): Map<number, number | null> {
  const m = new Map<number, number | null>();
  for (const p of points) {
    const w = isoWeek(new Date(p.date + "T00:00:00Z"));
    m.set(w, p.value);
  }
  return m;
}

export function buildRows(payload: InventoryPayload, unit: UnitChoice): Row[] {
  const avgByWeek = indexByWeek(payload.five_year_avg);
  const minByWeek = indexByWeek(payload.five_year_min);
  const maxByWeek = indexByWeek(payload.five_year_max);

  return payload.current.map((p) => {
    const w = isoWeek(new Date(p.date + "T00:00:00Z"));
    const cv = convert(p.value, unit);
    const av = convert(avgByWeek.get(w) ?? null, unit);
    const mn = convert(minByWeek.get(w) ?? null, unit);
    const mx = convert(maxByWeek.get(w) ?? null, unit);
    return {
      date: p.date,
      current: cv,
      avg: av,
      min: mn,
      max: mx,
      bandLow: mn,
      // recharts stacked Area trick: pass [low, high] via two areas
      bandHigh: mx != null && mn != null ? mx - mn : null,
    };
  });
}

function axisDate(iso: string): string {
  const d = new Date(iso + "T00:00:00Z");
  return d.toLocaleDateString("en-US", { month: "short", year: "2-digit", timeZone: "UTC" });
}

type Props = {
  payload: InventoryPayload;
  unit: UnitChoice;
  compact?: boolean;
};

export default function InventoryChart({ payload, unit, compact }: Props) {
  const rows = useMemo(() => buildRows(payload, unit), [payload, unit]);

  return (
    <ResponsiveContainer width="100%" height={compact ? 180 : 420}>
      <ComposedChart data={rows} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="var(--slate-100)" vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={axisDate}
          minTickGap={28}
          stroke="var(--slate-300)"
          tickLine={false}
        />
        <YAxis
          stroke="var(--slate-300)"
          tickLine={false}
          width={56}
          tickFormatter={(v) => fmtValue(v as number, unit)}
        />
        {/* 5y range band: drawn as a stack of two areas — invisible base + visible delta. */}
        <Area
          type="monotone"
          dataKey="bandLow"
          stackId="band"
          stroke="none"
          fill="transparent"
          isAnimationActive={false}
        />
        <Area
          type="monotone"
          dataKey="bandHigh"
          stackId="band"
          stroke="none"
          fill="var(--accent-soft)"
          fillOpacity={0.45}
          isAnimationActive={false}
          name="5y range"
        />
        <Line
          type="monotone"
          dataKey="avg"
          stroke="var(--slate-500)"
          strokeWidth={1.25}
          strokeDasharray="4 3"
          dot={false}
          isAnimationActive={false}
          name="5y avg"
        />
        <Line
          type="monotone"
          dataKey="current"
          stroke="var(--accent)"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
          name="Current"
        />
        <Tooltip
          cursor={{ stroke: "var(--slate-300)", strokeWidth: 1 }}
          labelFormatter={(l) => fmtDate(l as string)}
          formatter={(v: number, name) => {
            if (v == null) return ["—", name];
            return [fmtValue(v, unit) + " " + unit, name];
          }}
          contentStyle={{
            fontSize: 11,
            border: "1px solid var(--border)",
            borderRadius: 2,
          }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
