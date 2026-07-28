"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useAccount, useHealth } from "@/lib/api";
import { Icon } from "./Icon";

/** the avatar in the top-right. there is no sign-in here to open -- the backend holds one
 * authorised google account -- so this shows *which* account is wired up and whether the
 * services behind it are actually answering. */
export function AccountMenu({ onOpenConnection }: { onOpenConnection: () => void }) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const { data: account } = useAccount();
  const { data: health, error: healthError } = useHealth();

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const backendOk = healthError ? false : health?.ok;
  const initial = account?.email?.[0]?.toUpperCase();

  return (
    <div ref={wrapRef} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Connected account"
        className={`flex h-8 w-8 items-center justify-center overflow-hidden rounded-full border bg-surface-container-high text-sm font-semibold transition-colors ${
          open
            ? "border-primary text-on-surface"
            : "border-border-glass text-on-surface-variant hover:border-outline hover:text-on-surface"
        }`}
      >
        {initial ?? <Icon name="person" size={18} />}
      </button>

      {open && (
        <div
          role="menu"
          className="absolute top-11 right-0 z-50 w-72 rounded-xl border border-[rgba(226,232,240,0.15)] bg-surface-charcoal/90 p-3 shadow-[0_20px_40px_-10px_rgba(0,0,0,0.6)] backdrop-blur-xl"
        >
          <p className="font-label-sm text-label-sm text-primary uppercase">Connected account</p>
          <p className="mt-1 truncate text-sm text-on-surface">
            {account?.email ?? (account?.error ? "Not connected" : "Checking…")}
          </p>

          <div className="mt-3 flex flex-col gap-1.5 border-t border-border-glass pt-3">
            {account?.services.map((s) => (
              <div key={s.name} className="flex items-center justify-between text-xs">
                <span className="text-on-surface-variant">{s.name}</span>
                <span className={s.granted ? "text-secondary" : "text-error"}>
                  {s.granted ? "authorised" : "no scope"}
                </span>
              </div>
            ))}
            <div className="flex items-center justify-between text-xs">
              <span className="text-on-surface-variant">Backend</span>
              <span className={backendOk ? "text-secondary" : backendOk === false ? "text-error" : "text-outline"}>
                {backendOk === undefined ? "…" : backendOk ? "healthy" : "unreachable"}
              </span>
            </div>
          </div>

          <div className="mt-3 flex flex-col border-t border-border-glass pt-2">
            <button
              onClick={() => {
                setOpen(false);
                onOpenConnection();
              }}
              className="flex items-center gap-2 rounded px-2 py-1.5 text-left text-sm text-on-surface-variant transition-colors hover:bg-surface-container-high/50 hover:text-on-surface"
            >
              <Icon name="cable" size={16} /> Connection details
            </button>
            <Link
              href="/audit"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2 rounded px-2 py-1.5 text-sm text-on-surface-variant transition-colors hover:bg-surface-container-high/50 hover:text-on-surface"
            >
              <Icon name="receipt_long" size={16} /> Audit log
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
