"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useApprovals } from "@/lib/api";
import { Icon } from "./Icon";
import { GlanceMark } from "./GlanceMark";
import { NavCommandBar } from "./NavCommandBar";
import { AccountMenu } from "./AccountMenu";
import { SettingsDialog, type SettingsSection } from "./SettingsDialog";

const ROUTES = [
  { href: "/", label: "Dashboard" },
  { href: "/approvals", label: "Approvals" },
  { href: "/audit", label: "Audit" },
];

// the rail's first three map to the dashboard's columns rather than to routes -- on a wide
// screen all three are already on-screen, so these focus a column instead of navigating
const COLUMNS = [
  { icon: "inbox", label: "Inbox", id: "inbox" },
  { icon: "calendar_today", label: "Calendar", id: "calendar" },
  { icon: "assignment", label: "Tasks", id: "tasks" },
];

function focusColumn(id: string) {
  const el = document.getElementById(id);
  if (!el) return;
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  el.classList.add("panel-focus");
  window.setTimeout(() => el.classList.remove("panel-focus"), 1200);
  // hands the arrow keys to that column's scroller, which is the useful half on desktop
  // where scrollIntoView is a no-op because all three are already visible
  (el.querySelector("[data-panel-body]") as HTMLElement | null)?.focus({ preventScroll: true });
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { data: approvals } = useApprovals();
  const [settings, setSettings] = useState<SettingsSection | null>(null);
  const [pendingColumn, setPendingColumn] = useState<string | null>(null);

  const pending = approvals?.length ?? 0;

  // a column click from /audit has to land on the dashboard before it can focus anything
  useEffect(() => {
    if (pathname !== "/" || !pendingColumn) return;
    const t = window.setTimeout(() => {
      focusColumn(pendingColumn);
      setPendingColumn(null);
    }, 150);
    return () => window.clearTimeout(t);
  }, [pathname, pendingColumn]);

  const onColumn = useCallback(
    (id: string) => {
      if (pathname === "/") focusColumn(id);
      else {
        setPendingColumn(id);
        router.push("/");
      }
    },
    [pathname, router],
  );

  const railButton =
    "flex w-full flex-col items-center justify-center rounded-xl p-3 text-on-surface-variant transition-all duration-300 hover:bg-surface-container-high hover:text-on-surface";

  return (
    <>
      <nav className="fixed top-0 z-50 flex w-full max-w-[100vw] items-center justify-between border-b border-border-glass bg-background-obsidian/60 px-container-margin py-4 backdrop-blur-md">
        <div className="flex items-center gap-6">
          <Link href="/" aria-label="Glance" className="flex items-center">
            <GlanceMark size={30} className="transition-opacity hover:opacity-80" />
          </Link>
          <div className="hidden gap-4 sm:flex">
            {ROUTES.map((r) => {
              const active = pathname === r.href;
              return (
                <Link
                  key={r.href}
                  href={r.href}
                  className={
                    active
                      ? "border-b border-primary pb-1 font-bold text-on-surface transition-colors"
                      : "rounded px-2 py-1 font-medium text-on-surface-variant transition-colors hover:bg-surface-container-high/50 hover:text-on-surface"
                  }
                >
                  {r.label}
                </Link>
              );
            })}
          </div>
        </div>

        <div className="hidden max-w-2xl flex-1 px-6 lg:block">
          <NavCommandBar />
        </div>

        <div className="flex items-center gap-4">
          <Link
            href="/approvals"
            aria-label={pending ? `${pending} approvals waiting` : "Approvals"}
            className="relative rounded-full p-2 text-on-surface-variant transition-colors hover:bg-surface-container-high/50 hover:text-on-surface"
          >
            <Icon name="notifications" />
            {pending > 0 && (
              <span className="absolute top-0.5 right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary-container px-1 text-[10px] font-bold text-on-primary-container">
                {pending > 9 ? "9+" : pending}
              </span>
            )}
          </Link>
          <button
            onClick={() => setSettings("preferences")}
            aria-label="Settings"
            className="rounded-full p-2 text-on-surface-variant transition-colors hover:bg-surface-container-high/50 hover:text-on-surface"
          >
            <Icon name="settings" />
          </button>
          <AccountMenu onOpenConnection={() => setSettings("connection")} />
        </div>
      </nav>

      <aside className="fixed top-16 left-0 z-40 hidden h-[calc(100vh-64px)] w-20 flex-col items-center justify-between border-r border-border-glass bg-surface-container-lowest/60 py-stack-lg backdrop-blur-md md:flex">
        <div className="flex w-full flex-col gap-gutter px-2">
          {COLUMNS.map((item) => (
            <button key={item.id} onClick={() => onColumn(item.id)} className={railButton}>
              <Icon name={item.icon} className="mb-1" />
              <span className="font-label-md text-label-md">{item.label}</span>
            </button>
          ))}
          <Link
            href="/audit"
            className={
              pathname === "/audit"
                ? "flex w-full flex-col items-center justify-center rounded-xl bg-primary-container/20 p-3 text-primary transition-all duration-300"
                : railButton
            }
          >
            <Icon name="insights" className="mb-1" />
            <span className="font-label-md text-label-md">Insights</span>
          </Link>
        </div>
        <div className="mb-4 flex w-full flex-col gap-4 px-2">
          <button onClick={() => setSettings("shortcuts")} aria-label="Keyboard shortcuts" className={railButton}>
            <Icon name="help" />
          </button>
        </div>
      </aside>

      <main className="mt-16 h-[calc(100vh-64px)] flex-1 overflow-y-auto p-8 md:ml-20">{children}</main>

      <SettingsDialog section={settings} onSection={setSettings} onClose={() => setSettings(null)} />
    </>
  );
}
