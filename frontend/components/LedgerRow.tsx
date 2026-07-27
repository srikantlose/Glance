"use client";

import { useState } from "react";
import { Copy, Undo2 } from "lucide-react";
import type { LedgerRowData } from "@/lib/types";
import { fmtIST } from "@/lib/format";
import { Badge } from "./Badge";
import { PolicyPill } from "./PolicyPill";

const STATUS_TONE: Record<string, "success" | "warn" | "high" | "muted" | "accent"> = {
  executed: "success",
  queued: "warn",
  failed: "high",
  pending: "muted",
  undone: "muted",
};

export function LedgerRow({ row, onUndo }: { row: LedgerRowData; onUndo: (id: string) => Promise<void> }) {
  const [busy, setBusy] = useState(false);

  async function undo() {
    setBusy(true);
    try {
      await onUndo(row.id);
    } finally {
      setBusy(false);
    }
  }

  const alreadyUndone = row.status === "undone" || !!row.undone_at;
  const canUndo = !row.irreversible && !alreadyUndone && row.status === "executed";

  return (
    <tr className="border-b border-border text-sm hover:bg-surface-2">
      <td className="whitespace-nowrap px-3 py-2 text-muted">{fmtIST(row.created_at)}</td>
      <td className="px-3 py-2">{row.agent_name ?? row.actor}</td>
      <td className="px-3 py-2">{row.tool}</td>
      <td className="px-3 py-2">{row.operation}</td>
      <td className="px-3 py-2">
        {row.authorization_type === "policy" && row.authorization_ref ? (
          <PolicyPill policyId={row.authorization_ref} />
        ) : row.authorization_type === "approval" ? (
          <a href="/approvals" className="text-xs text-accent hover:underline">
            approval
          </a>
        ) : (
          <span className="text-xs text-muted" title={row.authorization_ref ?? undefined}>
            instruction
          </span>
        )}
      </td>
      <td className="px-3 py-2">
        {row.lyzr_trace_id ? (
          <button
            onClick={() => navigator.clipboard.writeText(row.lyzr_trace_id ?? "")}
            className="flex items-center gap-1 text-xs text-muted hover:text-text"
            title={row.lyzr_trace_id}
          >
            {row.lyzr_trace_id.slice(0, 8)} <Copy size={10} />
          </button>
        ) : (
          <span className="text-xs text-muted">--</span>
        )}
      </td>
      <td className="px-3 py-2">
        <Badge tone={STATUS_TONE[row.status] ?? "muted"}>{row.status}</Badge>
      </td>
      <td className="px-3 py-2">
        {alreadyUndone ? null : row.irreversible ? (
          <span className="text-xs text-muted" title="irreversible — draft a correction instead">
            irreversible
          </span>
        ) : (
          <button
            disabled={!canUndo || busy}
            onClick={undo}
            className="flex items-center gap-1 rounded border border-border px-2 py-1 text-xs hover:bg-surface disabled:opacity-40"
          >
            <Undo2 size={12} /> Undo
          </button>
        )}
      </td>
    </tr>
  );
}
