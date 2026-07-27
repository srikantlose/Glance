import useSWR from "swr";
import type { Approval, DashboardSnapshot, LedgerRowData, Policy } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

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

export function newIdempotencyKey(): string {
  return crypto.randomUUID();
}
