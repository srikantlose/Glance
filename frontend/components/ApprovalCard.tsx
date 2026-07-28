"use client";

import { useState } from "react";
import type { Approval } from "@/lib/types";
import { fmtIST } from "@/lib/format";
import { Icon } from "./Icon";

export function ApprovalCard({
  approval,
  onDecide,
}: {
  approval: Approval;
  onDecide: (id: string, action: "approve" | "reject") => Promise<void>;
}) {
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
    .map((a) =>
      a.operation === "send" ? "1 email" : a.operation === "task.create" ? "1 tracking task" : `${a.tool}.${a.operation}`,
    )
    .join(" + ");

  return (
    <div className="glance-row rounded border-border-glass bg-surface-container-lowest/50 p-4">
      <div className="mb-2 flex items-center justify-between text-xs text-on-surface-variant">
        <span>{fmtIST(approval.created_at)}</span>
        <span className="font-label-md text-label-md uppercase">{bundleLabel}</span>
      </div>

      <pre className="mb-3 rounded border border-border-glass bg-surface-container-lowest/60 p-3 text-sm whitespace-pre-wrap text-on-surface">
        {approval.preview.rendered}
      </pre>

      {approval.pii_findings.length > 0 && (
        <div className="mb-3 rounded border border-tertiary/30 bg-tertiary/10 p-2">
          <p className="mb-1 text-xs font-semibold text-tertiary">PII flagged and redacted before send</p>
          <ul className="space-y-0.5 text-xs">
            {approval.pii_findings.map((f, i) => (
              <li key={i} className="text-on-surface-variant">
                <span className="text-error line-through">{f.original}</span> →{" "}
                <span className="text-secondary">{f.redacted}</span>{" "}
                <span className="text-on-surface-variant">({f.flagged_by})</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex gap-2">
        <button
          disabled={busy}
          onClick={() => decide("approve")}
          className="flex items-center gap-1 rounded border border-secondary/30 bg-secondary/10 px-3 py-1.5 text-sm font-medium text-secondary transition-colors hover:bg-secondary/20 disabled:opacity-50"
        >
          <Icon name="check" size={14} /> Approve
        </button>
        <button
          disabled={busy}
          onClick={() => decide("reject")}
          className="flex items-center gap-1 rounded border border-error/30 bg-error-container/20 px-3 py-1.5 text-sm font-medium text-error transition-colors hover:bg-error/20 disabled:opacity-50"
        >
          <Icon name="close" size={14} /> Reject
        </button>
      </div>
    </div>
  );
}
