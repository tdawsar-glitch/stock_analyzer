import { useEffect, useMemo, useState } from "react";
import Sidebar from "./components/Sidebar";
import ChartCard from "./components/ChartCard";
import DeepDive from "./components/DeepDive";
import Reconcile from "./components/Reconcile";
import { fetchInventory, fetchMeta, triggerRefresh } from "./api";
import type {
  Frequency,
  InventoryPayload,
  Meta,
  UnitChoice,
} from "./types";
const DEFAULT_PRODUCTS = [
  "crude", "gasoline", "gasoil", "jet", "fuel_oil", "naphtha", "lpg",
];

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [metaError, setMetaError] = useState<string | null>(null);

  const [unit, setUnit] = useState<UnitChoice>("kb");
  const [frequency, setFrequency] = useState<Frequency>("weekly");
  const [selectedGeography, setSelectedGeography] = useState("global");
  const [selectedProducts, setSelectedProducts] = useState<Set<string>>(
    new Set(DEFAULT_PRODUCTS)
  );

  const [payloads, setPayloads] = useState<Record<string, InventoryPayload>>({});
  const [deepDive, setDeepDive] = useState<string | null>(null);

  // Initial meta load
  useEffect(() => {
    fetchMeta()
      .then((m) => {
        setMeta(m);
        // Auto-trim selected products to those that are configured.
        setSelectedProducts((prev) => {
          const next = new Set<string>();
          for (const p of m.products) {
            if (p.configured && (prev.size === 0 || prev.has(p.key))) next.add(p.key);
          }
          return next;
        });
      })
      .catch((e) => setMetaError(String(e)));
  }, []);

  // Load each (product, geography) when selection changes.
  useEffect(() => {
    if (!meta) return;
    const toLoad = Array.from(selectedProducts);
    let cancelled = false;

    setPayloads({});
    Promise.all(
      toLoad.map((p) =>
        fetchInventory(p, selectedGeography, frequency)
          .then((data) => [p, data] as const)
          .catch(() => null)
      )
    ).then((results) => {
      if (cancelled) return;
      const next: Record<string, InventoryPayload> = {};
      for (const r of results) {
        if (r) next[r[0]] = r[1];
      }
      setPayloads(next);
    });

    return () => { cancelled = true; };
  }, [meta, selectedProducts, selectedGeography, frequency]);

  const orderedProducts = useMemo(() => {
    if (!meta) return [];
    const order = new Map(meta.products.map((p, i) => [p.key, i]));
    return Array.from(selectedProducts).sort(
      (a, b) => (order.get(a) ?? 99) - (order.get(b) ?? 99)
    );
  }, [meta, selectedProducts]);

  const onRefresh = async () => {
    const token = window.prompt(
      "Enter admin token (set via ADMIN_TOKEN env var on the backend):"
    );
    if (!token) return;
    try {
      await triggerRefresh(token);
      window.location.reload();
    } catch (e) {
      alert("Refresh failed: " + e);
    }
  };

  const showReconcile = selectedGeography === "us" && selectedProducts.has("crude");

  return (
    <div className="app">
      <header className="topbar">
        <h1>Oil Inventory Tracker</h1>
        <div className="meta">
          <span>
            last refresh:{" "}
            {meta?.last_refresh
              ? new Date(meta.last_refresh).toLocaleString()
              : "—"}
          </span>
          <label>
            unit{" "}
            <select
              value={unit}
              onChange={(e) => setUnit(e.target.value as UnitChoice)}
            >
              <option value="kb">kb</option>
              <option value="mb">mb</option>
              <option value="bbl">bbl</option>
            </select>
          </label>
          <button onClick={onRefresh}>Refresh</button>
        </div>
      </header>

      <div className="layout">
        {meta ? (
          <Sidebar
            products={meta.products}
            geographies={meta.geographies}
            selectedProducts={selectedProducts}
            selectedGeography={selectedGeography}
            frequency={frequency}
            onToggleProduct={(k) =>
              setSelectedProducts((prev) => {
                const next = new Set(prev);
                next.has(k) ? next.delete(k) : next.add(k);
                return next;
              })
            }
            onSelectGeography={setSelectedGeography}
            onSelectFrequency={setFrequency}
          />
        ) : (
          <aside className="sidebar">
            {metaError ? `Error: ${metaError}` : "Loading…"}
          </aside>
        )}

        <main className="main">
          {showReconcile && <Reconcile />}

          {orderedProducts.length === 0 ? (
            <div className="empty-state">
              No products selected. Pick at least one in the sidebar.
              {meta && meta.products.every((p) => !p.configured) && (
                <>
                  <br /><br />
                  <strong>Setup required:</strong> populate Vortexa IDs in
                  <code> config/products.yaml</code> and
                  <code> config/geographies.yaml</code>, then run
                  <code> python -m scripts.backfill</code>.
                </>
              )}
            </div>
          ) : (
            <div className="grid">
              {orderedProducts.map((key) => {
                const payload = payloads[key];
                if (!payload) {
                  return (
                    <div className="chart-card" key={key}>
                      <div className="chart-header">
                        <div>
                          <span className="title">
                            {meta?.products.find((p) => p.key === key)?.label || key}
                          </span>
                        </div>
                      </div>
                      <div style={{ fontSize: 11, color: "var(--slate-500)" }}>
                        Loading…
                      </div>
                    </div>
                  );
                }
                return (
                  <ChartCard
                    key={key}
                    payload={payload}
                    unit={unit}
                    onOpen={() => setDeepDive(key)}
                  />
                );
              })}
            </div>
          )}
        </main>
      </div>

      {deepDive && payloads[deepDive] && (
        <DeepDive
          payload={payloads[deepDive]}
          unit={unit}
          onClose={() => setDeepDive(null)}
        />
      )}

    </div>
  );
}
