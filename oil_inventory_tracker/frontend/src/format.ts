import type { UnitChoice } from "./types";

const BBL_PER_KB = 1_000;
const BBL_PER_MB = 1_000_000;

export function convert(valueBbl: number | null, unit: UnitChoice): number | null {
  if (valueBbl == null) return null;
  if (unit === "kb") return valueBbl / BBL_PER_KB;
  if (unit === "mb") return valueBbl / BBL_PER_MB;
  return valueBbl;
}

export function fmtUnit(unit: UnitChoice): string {
  return { kb: "kb", mb: "mb", bbl: "bbl" }[unit];
}

const nf0 = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const nf1 = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });
const pf = new Intl.NumberFormat("en-US", {
  style: "percent",
  maximumFractionDigits: 1,
  signDisplay: "exceptZero",
});

export function fmtValue(value: number | null, unit: UnitChoice): string {
  if (value == null) return "—";
  const formatter = unit === "mb" ? nf1 : nf0;
  return formatter.format(value);
}

export function fmtPct(value: number | null | undefined): string {
  if (value == null) return "—";
  return pf.format(value);
}

export function fmtSignedAbs(
  value: number | null | undefined,
  unit: UnitChoice
): string {
  if (value == null) return "—";
  const formatter = unit === "mb" ? nf1 : nf0;
  return (value >= 0 ? "+" : "") + formatter.format(value);
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso + "T00:00:00Z").toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}
