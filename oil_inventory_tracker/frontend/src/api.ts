import type {
  Frequency,
  InventoryPayload,
  Meta,
  Reconciliation,
} from "./types";

async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}: ${url}`);
  return r.json();
}

export async function fetchMeta(): Promise<Meta> {
  return getJSON<Meta>("/api/meta");
}

export async function fetchInventory(
  product: string,
  geography: string,
  frequency: Frequency
): Promise<InventoryPayload> {
  const q = new URLSearchParams({ product, geography, frequency });
  return getJSON<InventoryPayload>(`/api/inventory?${q}`);
}

export async function fetchReconciliation(): Promise<Reconciliation> {
  return getJSON<Reconciliation>("/api/reconcile/us_crude");
}

export function csvUrl(product: string, geography: string): string {
  const q = new URLSearchParams({ product, geography });
  return `/api/inventory/csv?${q}`;
}

export async function triggerRefresh(token: string): Promise<void> {
  const r = await fetch("/api/refresh?mode=incremental", {
    method: "POST",
    headers: { "x-admin-token": token },
  });
  if (!r.ok) throw new Error(`refresh failed: ${r.status}`);
}
