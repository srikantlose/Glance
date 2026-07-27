"use client";

import { useState } from "react";
import { Check, X } from "lucide-react";
import type { Approval } from "@/lib/types";
import { fmtIST } from "@/lib/format";

export function ApprovalCard({ approval, onDecide }: { approval: Approval; onDecide: (id: string, action: "approve" | "reject") => Promise<void> }) {
  const [busy, setBusy] = useState(false);

  async function decide(action: "approve" | "reject") {
    setBusy(true);
    try {
      await onDecide(approval.id, action);
    } finally {
      setBusy(false);
    }
  }

  const bundleLabel = approval.preview.actions
    .map((a) => (a.operation === "send" ? "1 email" : a.operation === "task.create" ? "1 tracking task" : `${a.tool}.${a.operation}`))
    .join(" + ");

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="mb-2 flex items-center justify-between text-xs text-muted">
        <span>{fmtIST(approval.created_at)}</span>
        <span>{bundleLabel}</span>
      </div>

      <pre className="mb-3 whitespace-pre-wrap rounded-md bg-surface-2 p-3 text-sm text-text">{approval.preview.rendered}</pre>

      {approval.pii_findings.length > 0 && (
        <div className="mb-3 rounded-md border border-warn/30 bg-warn/10 p-2">
          <p className="mb-1 text-xs font-medium text-warn">PII flagged and redacted before send</p>
          <ul className="space-y-0.5 text-xs">
            {approval.pii_findings.map((f, i) => (
              <li key={i} className="text-muted">
                <span className="text-high line-through">{f.original}</span> → <span className="text-success">{f.redacted}</span>{" "}
                <span className="text-muted">({f.flagged_by})</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex gap-2">
        <button
          disabled={busy}
          onClick={() => decide("approve")}
          className="flex items-center gap-1 rounded bg-success/15 px-3 py-1.5 text-sm font-medium text-success hover:bg-success/25 disabled:opacity-50"
        >
          <Check size={14} /> Approve
        </button>
        <button
          disabled={busy}
          onClick={() => decide("reject")}
          className="flex items-center gap-1 rounded bg-high/15 px-3 py-1.5 text-sm font-medium text-high hover:bg-high/25 disabled:opacity-50"
        >
          <X size={14} /> Reject
        </button>
      </div>
    </div>
  );
}
