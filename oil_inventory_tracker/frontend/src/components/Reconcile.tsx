import { useEffect, useState } from "react";
import type { Reconciliation } from "../types";
import { fetchReconciliation } from "../api";
import { fmtDate, fmtPct } from "../format";

export default function Reconcile() {
  const [data, setData] = useState<Reconciliation | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchReconciliation()
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);

  if (error || !data) return null;
  if (!data.comparison) {
    // EIA key not configured or no overlap — render a quiet hint instead of nothing.
    return (
      <div className="reconcile">
        <div className="title">US crude data quality</div>
        <div>
          EIA reconciliation unavailable
          {!data.eia ? " (set EIA_API_KEY)" : ""}
          {data.vortexa_latest == null ? " · no Vortexa US crude cached yet" : ""}.
        </div>
      </div>
    );
  }

  const c = data.comparison;
  const ok = Math.abs(c.delta_pct || 0) < 0.05;
  return (
    <div className="reconcile">
      <div className="title">
        US crude: Vortexa vs EIA{" "}
        <span
          style={{
            marginLeft: 6,
            color: ok ? "var(--good)" : "var(--warn)",
            fontWeight: 600,
          }}
        >
          {ok ? "in line" : "diverging"}
        </span>
      </div>
      <div>
        Vortexa {(c.vortexa_bbl / 1_000_000).toFixed(1)} mb (as of {fmtDate(data.vortexa_as_of)})
        {" · "}
        EIA {(c.eia_bbl / 1_000_000).toFixed(1)} mb (as of {fmtDate(c.eia_as_of)})
        {" · Δ "}
        {(c.delta_bbl / 1_000_000).toFixed(1)} mb ({fmtPct(c.delta_pct)})
      </div>
    </div>
  );
}
