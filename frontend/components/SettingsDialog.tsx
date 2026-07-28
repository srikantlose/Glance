"use client";

import { useEffect } from "react";
import { API_BASE, useAccount, useHealth, usePolicies } from "@/lib/api";
import type { Policy } from "@/lib/types";
import { Badge } from "./Badge";
import { EmptyState } from "./EmptyState";
import { Icon } from "./Icon";

export type SettingsSection = "preferences" | "shortcuts" | "connection";

const TABS: { key: SettingsSection; label: string; icon: string }[] = [
  { key: "preferences", label: "Preferences", icon: "rule" },
  { key: "shortcuts", label: "Shortcuts", icon: "keyboard" },
  { key: "connection", label: "Connection", icon: "cable" },
];

const SHORTCUTS = [
  { keys: ["Ctrl", "Space"], label: "Hold to arm the agent pointer" },
  { keys: ["move"], label: "While armed, move over a row to lock onto it" },
  { keys: ["release"], label: "Let go to open the prompt on the locked row" },
  { keys: ["Esc"], label: "Close the prompt without sending" },
  { keys: ["hover"], label: "Rest on a row for its triage read" },
];

function Dot({ ok }: { ok: boolean | undefined }) {
  const tone =
    ok === undefined ? "bg-outline" : ok ? "bg-secondary shadow-[0_0_6px] shadow-secondary/60" : "bg-error";
  return <span className={`inline-block h-1.5 w-1.5 shrink-0 rounded-full ${tone}`} />;
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-border-glass py-2.5 last:border-b-0">
      <span className="text-sm text-on-surface-variant">{label}</span>
      <span className="flex min-w-0 items-center gap-2 text-sm text-on-surface">{children}</span>
    </div>
  );
}

function Preferences() {
  const { data, error, isLoading } = usePolicies();

  if (error) return <EmptyState icon="error" label="Couldn't load preferences." />;
  if (isLoading && !data) return <p className="py-6 text-sm text-on-surface-variant">Loading…</p>;
  if (!data?.length)
    return <EmptyState icon="rule" label="No standing preferences yet. Teach Glance one from a clarification." />;

  const sorted = [...data].sort((a: Policy, b: Policy) => b.times_applied - a.times_applied);

  return (
    <>
      <p className="mb-3 text-sm text-on-surface-variant">
        Standing instructions the agent checks before it acts. These are what a cited policy points at.
      </p>
      <ul className="flex flex-col gap-2">
        {sorted.map((p) => (
          <li key={p.id} className="rounded border border-border-glass bg-surface-container-lowest/50 p-3">
            <p className="text-sm text-on-surface">{p.text}</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Badge tone="muted">{p.scope}</Badge>
              <Badge tone={p.provenance === "explicit" ? "accent" : "low"}>{p.provenance}</Badge>
              <span className="text-xs text-on-surface-variant">
                applied {p.times_applied}×
              </span>
            </div>
          </li>
        ))}
      </ul>
    </>
  );
}

function Shortcuts() {
  return (
    <>
      <p className="mb-3 text-sm text-on-surface-variant">
        Glance is driven from a second pointer that shadows yours. You never have to leave the row
        you're looking at.
      </p>
      <ul className="flex flex-col">
        {SHORTCUTS.map((s) => (
          <li
            key={s.label}
            className="flex items-center justify-between gap-4 border-b border-border-glass py-2.5 last:border-b-0"
          >
            <span className="text-sm text-on-surface">{s.label}</span>
            <span className="flex shrink-0 gap-1">
              {s.keys.map((k) => (
                <kbd
                  key={k}
                  className="rounded border border-border-glass bg-surface-container-high/60 px-1.5 py-0.5 font-label-sm text-label-sm text-on-surface-variant uppercase"
                >
                  {k}
                </kbd>
              ))}
            </span>
          </li>
        ))}
      </ul>
    </>
  );
}

function Connection() {
  const { data: account } = useAccount();
  const { data: health, error: healthError } = useHealth();
  const reachable = healthError ? false : health?.ok;

  return (
    <>
      <Row label="Google account">
        {account?.email ? (
          <span className="truncate">{account.email}</span>
        ) : (
          <span className="text-on-surface-variant">not connected</span>
        )}
        <Dot ok={account?.connected} />
      </Row>
      {account?.services.map((s) => (
        <Row key={s.name} label={s.name}>
          <span className="truncate text-on-surface-variant">{s.scope ?? "no scope granted"}</span>
          <Dot ok={s.granted} />
        </Row>
      ))}
      <Row label="Backend">
        <span className="truncate text-on-surface-variant">{API_BASE}</span>
        <Dot ok={reachable} />
      </Row>
      <Row label="Ledger (Postgres)">
        <Dot ok={healthError ? false : health?.db} />
      </Row>
      <Row label="Memory (Qdrant)">
        <Dot ok={healthError ? false : health?.qdrant} />
      </Row>

      {account?.error && (
        <p className="mt-3 rounded border border-error/30 bg-error-container/20 p-2 text-xs text-error">
          {account.error}
        </p>
      )}
      <p className="mt-4 text-xs text-on-surface-variant">
        Glance runs against one authorised Google account held by the backend — there are no
        per-user sessions, so there is nothing to sign in or out of here.
      </p>
    </>
  );
}

interface Props {
  section: SettingsSection | null;
  onSection: (s: SettingsSection) => void;
  onClose: () => void;
}

export function SettingsDialog({ section, onSection, onClose }: Props) {
  useEffect(() => {
    if (!section) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [section, onClose]);

  if (!section) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Settings"
      className="fixed inset-0 z-[10001] flex items-center justify-center p-4"
    >
      <div className="absolute inset-0 bg-background-obsidian/70 backdrop-blur-sm" onClick={onClose} />

      <div className="relative flex max-h-[80vh] w-full max-w-xl flex-col overflow-hidden rounded-xl border border-[rgba(226,232,240,0.15)] bg-surface-charcoal/90 shadow-[0_20px_40px_-10px_rgba(0,0,0,0.6)] backdrop-blur-xl">
        <div className="flex items-center justify-between border-b border-border-glass px-4 py-3">
          <h2 className="font-headline-md text-headline-md text-on-surface">Settings</h2>
          <button
            onClick={onClose}
            aria-label="Close settings"
            className="rounded-full p-1 text-on-surface-variant transition-colors hover:bg-surface-container-high/50 hover:text-on-surface"
          >
            <Icon name="close" size={18} />
          </button>
        </div>

        <div className="flex gap-1 border-b border-border-glass px-3 pt-2">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => onSection(t.key)}
              className={
                section === t.key
                  ? "flex items-center gap-1.5 border-b-2 border-primary px-3 py-2 text-sm font-semibold text-on-surface"
                  : "flex items-center gap-1.5 border-b-2 border-transparent px-3 py-2 text-sm text-on-surface-variant transition-colors hover:text-on-surface"
              }
            >
              <Icon name={t.icon} size={16} />
              {t.label}
            </button>
          ))}
        </div>

        <div className="overflow-y-auto p-4">
          {section === "preferences" && <Preferences />}
          {section === "shortcuts" && <Shortcuts />}
          {section === "connection" && <Connection />}
        </div>
      </div>
    </div>
  );
}
