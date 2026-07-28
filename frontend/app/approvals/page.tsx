"use client";

import { apiFetch, useApprovals } from "@/lib/api";
import { ApprovalCard } from "@/components/ApprovalCard";
import { EmptyState, ErrorStrip } from "@/components/EmptyState";
import { Panel } from "@/components/Panel";

export default function ApprovalsPage() {
  const { data, error, isLoading, mutate } = useApprovals();

  async function decide(id: string, action: "approve" | "reject") {
    await apiFetch(`/api/approvals/${id}/${action}`, { method: "POST" });
    mutate();
  }

  return (
    <div className="mx-auto h-full max-w-3xl">
      <Panel title="Approvals">
        {error && <ErrorStrip message="Couldn't reach the backend." onRetry={() => mutate()} />}
        {isLoading && !data && <p className="p-3 text-xs text-on-surface-variant">Loading…</p>}
        {data && data.length === 0 && <EmptyState icon="verified_user" label="Nothing waiting on you" />}

        <div className="flex flex-col gap-3 p-1">
          {data?.map((approval) => (
            <ApprovalCard key={approval.id} approval={approval} onDecide={decide} />
          ))}
        </div>
      </Panel>
    </div>
  );
}
