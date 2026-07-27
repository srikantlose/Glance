"use client";

import { ShieldCheck } from "lucide-react";
import { apiFetch, useApprovals } from "@/lib/api";
import { ApprovalCard } from "@/components/ApprovalCard";
import { EmptyState, ErrorStrip } from "@/components/EmptyState";

export default function ApprovalsPage() {
  const { data, error, isLoading, mutate } = useApprovals();

  async function decide(id: string, action: "approve" | "reject") {
    await apiFetch(`/api/approvals/${id}/${action}`, { method: "POST" });
    mutate();
  }

  return (
    <div className="mx-auto max-w-2xl p-4">
      <h1 className="mb-4 text-lg font-semibold">Approvals</h1>

      {error && <ErrorStrip message="Couldn't reach the backend." onRetry={() => mutate()} />}
      {isLoading && <p className="text-sm text-muted">Loading…</p>}
      {data && data.length === 0 && <EmptyState icon={ShieldCheck} label="Nothing waiting on you" />}

      <div className="flex flex-col gap-3">
        {data?.map((approval) => (
          <ApprovalCard key={approval.id} approval={approval} onDecide={decide} />
        ))}
      </div>
    </div>
  );
}
