"use client";

import { useState } from "react";
import { usePolicies } from "@/lib/api";
import { Icon } from "./Icon";

export function PolicyPill({ policyId, policyText }: { policyId: string; policyText?: string | null }) {
  const [open, setOpen] = useState(false);
  const { data: policies } = usePolicies();

  const resolvedText = policyText ?? policies?.find((p) => p.id === policyId)?.text ?? null;

  return (
    <span className="relative inline-block">
      <button
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1 rounded border border-primary/30 bg-primary-container/20 px-2 py-0.5 text-[10px] font-bold tracking-wider text-primary uppercase hover:bg-primary-container/30"
      >
        <Icon name="bookmark" size={11} />
        policy
      </button>
      {open && (
        <div className="absolute top-full left-0 z-20 mt-1 w-64 rounded-xl border border-border-glass bg-surface-charcoal/90 p-3 text-xs text-on-surface shadow-[0_20px_40px_-10px_rgba(0,0,0,0.6)] backdrop-blur-xl">
          {resolvedText ?? "Loading policy text…"}
          <button
            onClick={() => setOpen(false)}
            className="mt-2 block text-on-surface-variant hover:text-on-surface"
          >
            close
          </button>
        </div>
      )}
    </span>
  );
}
