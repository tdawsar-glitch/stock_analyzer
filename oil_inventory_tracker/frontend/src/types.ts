export type Point = { date: string; value: number | null };

export type ProductMeta = {
  key: string;
  label: string;
  display_unit: "kb" | "mb" | "bbl";
  configured: boolean;
};

export type GeographyMeta = {
  key: string;
  label: string;
  kind: "global" | "region" | "country" | "hub";
  configured: boolean;
  eia_reconcile: boolean;
};

export type Meta = {
  last_refresh: string | null;
  demo_mode?: boolean;
  vortexa_key_set?: boolean;
  products: ProductMeta[];
  geographies: GeographyMeta[];
};

export type Summary = {
  latest_date?: string;
  latest_value?: number;
  yoy_delta?: { abs: number; pct: number } | null;
  vs_avg_delta?: { abs: number; pct: number } | null;
  percentile_in_5y_range?: number | null;
};

export type InventoryPayload = {
  metadata: {
    product_key: string;
    product_label: string;
    geography_key: string;
    geography_label: string;
    display_unit: "kb" | "mb" | "bbl";
    unit_base: "bbl";
    source: string;
    frequency: "daily" | "weekly" | "monthly";
    last_observation: string | null;
    rows_cached: number;
  };
  current: Point[];
  five_year_avg: Point[];
  five_year_max: Point[];
  five_year_min: Point[];
  prior_years: Record<string, Point[]>;
  partial: boolean;
  summary: Summary;
};

export type Reconciliation = {
  vortexa_latest: number | null;
  vortexa_as_of: string | null;
  eia: { as_of: string; value_bbl: number; source: string } | null;
  comparison: {
    vortexa_bbl: number;
    eia_bbl: number;
    eia_as_of: string;
    delta_bbl: number;
    delta_pct: number | null;
  } | null;
};

export type UnitChoice = "kb" | "mb" | "bbl";
export type Frequency = "weekly" | "monthly";
