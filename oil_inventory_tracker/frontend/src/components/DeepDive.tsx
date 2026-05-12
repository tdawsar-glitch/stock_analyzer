import type { InventoryPayload, UnitChoice } from "../types";
import { convert, fmtPct, fmtSignedAbs, fmtValue, fmtDate } from "../format";
import InventoryChart from "./InventoryChart";
import { csvUrl } from "../api";

type Props = {
  payload: InventoryPayload;
  unit: UnitChoice;
  onClose: () => void;
};

export default function DeepDive({ payload, unit, onClose }: Props) {
  const m = payload.metadata;
  const s = payload.summary || {};
  const latestVal = convert(s.latest_value ?? null, unit);

  return (
    <div className="deep-dive-overlay" onClick={onClose}>
      <div className="deep-dive-modal" onClick={(e) => e.stopPropagation()}>
        <header>
          <h2>
            {m.product_label} · {m.geography_label}
            {payload.partial && <span className="badge" style={{ marginLeft: 8 }}>data partial</span>}
          </h2>
          <div style={{ display: "flex", gap: 8 }}>
            <a
              className="topbar-link"
              href={csvUrl(m.product_key, m.geography_key)}
              style={{
                fontSize: 12,
                padding: "4px 10px",
                border: "1px solid var(--border)",
                borderRadius: 2,
                textDecoration: "none",
                color: "var(--slate-900)",
              }}
            >
              Download CSV
            </a>
            <button onClick={onClose} style={{ fontSize: 12, padding: "4px 10px" }}>Close</button>
          </div>
        </header>

        <div className="stats">
          <div className="stat">
            <div className="label">Latest ({fmtDate(s.latest_date)})</div>
            <div className="value">{fmtValue(latestVal, unit)} {unit}</div>
          </div>
          <div className="stat">
            <div className="label">YoY</div>
            <div className="value">
              {s.yoy_delta ? (
                <>
                  {fmtSignedAbs(convert(s.yoy_delta.abs, unit), unit)} {unit}
                  <span style={{ fontSize: 12, marginLeft: 6, color: "var(--slate-500)" }}>
                    ({fmtPct(s.yoy_delta.pct)})
                  </span>
                </>
              ) : "—"}
            </div>
          </div>
          <div className="stat">
            <div className="label">vs 5y Avg</div>
            <div className="value">
              {s.vs_avg_delta ? (
                <>
                  {fmtSignedAbs(convert(s.vs_avg_delta.abs, unit), unit)} {unit}
                  <span style={{ fontSize: 12, marginLeft: 6, color: "var(--slate-500)" }}>
                    ({fmtPct(s.vs_avg_delta.pct)})
                  </span>
                </>
              ) : "—"}
            </div>
          </div>
          <div className="stat">
            <div className="label">5y range percentile</div>
            <div className="value">
              {s.percentile_in_5y_range != null
                ? `${Math.round(s.percentile_in_5y_range * 100)}%`
                : "—"}
            </div>
          </div>
        </div>

        <div className="chart-wrap">
          <InventoryChart payload={payload} unit={unit} />
        </div>

        <div style={{ fontSize: 11, color: "var(--slate-500)", marginTop: 8 }}>
          Source: {m.source} · {m.rows_cached.toLocaleString()} cached observations ·
          last obs {fmtDate(m.last_observation)} · frequency {m.frequency}
        </div>
      </div>
    </div>
  );
}
