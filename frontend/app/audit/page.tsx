"use client";

import { ScrollText } from "lucide-react";
import { apiFetch, useAudit } from "@/lib/api";
import { LedgerRow } from "@/components/LedgerRow";
import { EmptyState, ErrorStrip } from "@/components/EmptyState";

export default function AuditPage() {
  const { data, error, isLoading, mutate } = useAudit();

  async function undo(actionId: string) {
    try {
      await apiFetch(`/api/audit/${actionId}/undo`, { method: "POST" });
    } finally {
      mutate();
    }
  }

  return (
    <div className="p-4">
      <h1 className="mb-4 text-lg font-semibold">Audit</h1>

      {error && <ErrorStrip message="Couldn't reach the backend." onRetry={() => mutate()} />}
      {isLoading && <p className="text-sm text-muted">Loading…</p>}
      {data && data.length === 0 && <EmptyState icon={ScrollText} label="No actions logged yet" />}

      {data && data.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
                <th className="px-3 py-2">Time</th>
                <th className="px-3 py-2">Agent</th>
                <th className="px-3 py-2">Tool</th>
                <th className="px-3 py-2">Operation</th>
                <th className="px-3 py-2">Authorization</th>
                <th className="px-3 py-2">Trace</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Undo</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <LedgerRow key={row.id} row={row} onUndo={undo} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
