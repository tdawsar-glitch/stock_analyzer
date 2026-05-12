import type { InventoryPayload, UnitChoice } from "../types";
import { convert, fmtPct, fmtSignedAbs, fmtValue } from "../format";
import InventoryChart from "./InventoryChart";

type Props = {
  payload: InventoryPayload;
  unit: UnitChoice;
  onOpen: () => void;
};

export default function ChartCard({ payload, unit, onOpen }: Props) {
  const m = payload.metadata;
  const s = payload.summary || {};
  const latestVal = convert(s.latest_value ?? null, unit);
  const yoy = s.yoy_delta;
  const vsAvg = s.vs_avg_delta;

  return (
    <div className="chart-card" onClick={onOpen} role="button" tabIndex={0}>
      <div className="chart-header">
        <div>
          <span className="title">{m.product_label}</span>
          <span className="subtitle">· {m.geography_label}</span>
        </div>
        {payload.partial && <span className="badge">data partial</span>}
      </div>

      <div className="delta-line">
        <span>
          <span className="label">latest</span>
          {fmtValue(latestVal, unit)} {unit}
        </span>
        <span>
          <span className="label">yoy</span>
          {yoy ? (
            <span className={`delta ${yoy.abs >= 0 ? "up" : "down"}`}>
              {fmtSignedAbs(convert(yoy.abs, unit), unit)} ({fmtPct(yoy.pct)})
            </span>
          ) : "—"}
        </span>
        <span>
          <span className="label">vs 5y avg</span>
          {vsAvg ? (
            <span className={`delta ${vsAvg.abs >= 0 ? "up" : "down"}`}>
              {fmtSignedAbs(convert(vsAvg.abs, unit), unit)} ({fmtPct(vsAvg.pct)})
            </span>
          ) : "—"}
        </span>
      </div>

      <InventoryChart payload={payload} unit={unit} compact />
    </div>
  );
}
