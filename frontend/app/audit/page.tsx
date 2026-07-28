"use client";

import { apiFetch, useAudit } from "@/lib/api";
import { LedgerRow } from "@/components/LedgerRow";
import { EmptyState, ErrorStrip } from "@/components/EmptyState";
import { Panel } from "@/components/Panel";

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
    <div className="mx-auto h-full max-w-[1800px]">
      <Panel title="Audit">
        {error && <ErrorStrip message="Couldn't reach the backend." onRetry={() => mutate()} />}
        {isLoading && !data && <p className="p-3 text-xs text-on-surface-variant">Loading…</p>}
        {data && data.length === 0 && <EmptyState icon="receipt_long" label="No actions logged yet" />}

        {data && data.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-border-glass text-left text-xs tracking-wider text-on-surface-variant uppercase">
                  <th className="px-3 py-2 font-semibold">Time</th>
                  <th className="px-3 py-2 font-semibold">Agent</th>
                  <th className="px-3 py-2 font-semibold">Tool</th>
                  <th className="px-3 py-2 font-semibold">Operation</th>
                  <th className="px-3 py-2 font-semibold">Authorization</th>
                  <th className="px-3 py-2 font-semibold">Trace</th>
                  <th className="px-3 py-2 font-semibold">Status</th>
                  <th className="px-3 py-2 font-semibold">Undo</th>
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
      </Panel>
    </div>
  );
}
