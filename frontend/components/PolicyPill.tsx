"use client";

import { useState } from "react";
import { BookMarked } from "lucide-react";
import { usePolicies } from "@/lib/api";

export function PolicyPill({ policyId, policyText }: { policyId: string; policyText?: string | null }) {
  const [open, setOpen] = useState(false);
  const { data: policies } = usePolicies();

  const resolvedText = policyText ?? policies?.find((p) => p.id === policyId)?.text ?? null;

  return (
    <span className="relative inline-block">
      <button
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1 rounded-full border border-accent/30 bg-accent/10 px-2 py-0.5 text-xs text-accent hover:bg-accent/20"
      >
        <BookMarked size={11} />
        policy
      </button>
      {open && (
        <div className="absolute left-0 top-full z-20 mt-1 w-64 rounded-md border border-border bg-surface-2 p-3 text-xs text-text shadow-lg">
          {resolvedText ?? "Loading policy text…"}
          <button onClick={() => setOpen(false)} className="mt-2 block text-muted hover:text-text">
            close
          </button>
        </div>
      )}
    </span>
  );
}
