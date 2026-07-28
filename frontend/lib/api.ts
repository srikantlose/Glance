import useSWR from "swr";
import type { AccountInfo, Approval, DashboardSnapshot, HealthInfo, LedgerRowData, Policy } from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

const fetcher = <T,>(path: string) => apiFetch<T>(path);

export function useDashboard() {
  return useSWR<DashboardSnapshot>("/api/dashboard", fetcher, { refreshInterval: 5000 });
}

export function useApprovals() {
  return useSWR<Approval[]>("/api/approvals", fetcher, { refreshInterval: 5000 });
}

export function useAudit(limit = 100) {
  return useSWR<LedgerRowData[]>(`/api/audit?limit=${limit}`, fetcher, { refreshInterval: 5000 });
}

export function usePolicies() {
  return useSWR<Policy[]>("/api/policies", fetcher, { refreshInterval: 15000 });
}

/** the connected google account is fixed for the life of the backend process, so once it
 * resolves there's nothing to poll for. a failed token refresh still answers 200 with an
 * `error` field though, and swr won't retry a 200 -- so keep polling until it connects. */
export function useAccount() {
  return useSWR<AccountInfo>("/api/account", fetcher, {
    refreshInterval: (data) => (data?.connected ? 0 : 5000),
    revalidateOnFocus: false,
  });
}

export function useHealth() {
  return useSWR<HealthInfo>("/healthz", fetcher, { refreshInterval: 30000 });
}

export function newIdempotencyKey(): string {
  return crypto.randomUUID();
}
