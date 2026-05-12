import type { Frequency, GeographyMeta, ProductMeta } from "../types";

type Props = {
  products: ProductMeta[];
  geographies: GeographyMeta[];
  selectedProducts: Set<string>;
  selectedGeography: string;
  frequency: Frequency;
  onToggleProduct: (key: string) => void;
  onSelectGeography: (key: string) => void;
  onSelectFrequency: (f: Frequency) => void;
};

function groupGeographies(gs: GeographyMeta[]): Record<string, GeographyMeta[]> {
  const order = ["global", "region", "country", "hub"];
  const groups: Record<string, GeographyMeta[]> = {};
  for (const g of gs) groups[g.kind] = (groups[g.kind] || []).concat(g);
  // Stable ordering
  return Object.fromEntries(order.filter((k) => groups[k]).map((k) => [k, groups[k]!]));
}

const KIND_LABEL: Record<string, string> = {
  global: "Global",
  region: "Region",
  country: "Country",
  hub: "Hub",
};

export default function Sidebar(props: Props) {
  const groups = groupGeographies(props.geographies);

  return (
    <aside className="sidebar">
      <section>
        <h2>Geography</h2>
        <select
          value={props.selectedGeography}
          onChange={(e) => props.onSelectGeography(e.target.value)}
        >
          {Object.entries(groups).map(([kind, items]) => (
            <optgroup key={kind} label={KIND_LABEL[kind] || kind}>
              {items.map((g) => (
                <option key={g.key} value={g.key} disabled={!g.configured}>
                  {g.label}{!g.configured ? "  (id missing)" : ""}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </section>

      <section>
        <h2>Products</h2>
        {props.products.map((p) => (
          <label className="row" key={p.key}>
            <input
              type="checkbox"
              checked={props.selectedProducts.has(p.key)}
              disabled={!p.configured}
              onChange={() => props.onToggleProduct(p.key)}
            />
            <span>{p.label}{!p.configured ? "  (id missing)" : ""}</span>
          </label>
        ))}
      </section>

      <section>
        <h2>Frequency</h2>
        <div className="toggle-row">
          {(["weekly", "monthly"] as Frequency[]).map((f) => (
            <button
              key={f}
              className={props.frequency === f ? "active" : ""}
              onClick={() => props.onSelectFrequency(f)}
            >
              {f === "weekly" ? "Weekly" : "Monthly"}
            </button>
          ))}
        </div>
      </section>
    </aside>
  );
}
