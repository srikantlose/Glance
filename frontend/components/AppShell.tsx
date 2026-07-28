"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon } from "./Icon";
import { GlanceMark } from "./GlanceMark";
import { NavCommandBar } from "./NavCommandBar";

const ROUTES = [
  { href: "/", label: "Dashboard" },
  { href: "/approvals", label: "Approvals" },
  { href: "/audit", label: "Audit" },
];

const RAIL = [
  { icon: "inbox", label: "Inbox", href: "/#inbox" },
  { icon: "calendar_today", label: "Calendar", href: "/#calendar" },
  { icon: "assignment", label: "Tasks", href: "/#tasks" },
  { icon: "insights", label: "Insights", href: "/audit" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

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
            className="rounded-full p-2 text-on-surface-variant transition-colors hover:bg-surface-container-high/50 hover:text-on-surface"
          >
            <Icon name="notifications" />
          </Link>
          <button className="rounded-full p-2 text-on-surface-variant transition-colors hover:bg-surface-container-high/50 hover:text-on-surface">
            <Icon name="settings" />
          </button>
          <div className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-full border border-border-glass bg-surface-container-high text-on-surface-variant">
            <Icon name="person" size={18} />
          </div>
        </div>
      </nav>

      <aside className="fixed top-16 left-0 z-40 hidden h-[calc(100vh-64px)] w-20 flex-col items-center justify-between border-r border-border-glass bg-surface-container-lowest/60 py-stack-lg backdrop-blur-md md:flex">
        <div className="flex w-full flex-col gap-gutter px-2">
          {RAIL.map((item) => (
            <Link
              key={item.label}
              href={item.href}
              className="flex w-full flex-col items-center justify-center rounded-xl p-3 text-on-surface-variant transition-all duration-300 hover:bg-surface-container-high"
            >
              <Icon name={item.icon} className="mb-1" />
              <span className="font-label-md text-label-md">{item.label}</span>
            </Link>
          ))}
        </div>
        <div className="mb-4 flex w-full flex-col gap-4 px-2">
          <button className="flex w-full flex-col items-center justify-center rounded-xl p-3 text-on-surface-variant transition-all duration-300 hover:bg-surface-container-high">
            <Icon name="help" />
          </button>
          <button className="flex w-full flex-col items-center justify-center rounded-xl p-3 text-on-surface-variant transition-all duration-300 hover:bg-surface-container-high">
            <Icon name="logout" />
          </button>
        </div>
      </aside>

      <main className="mt-16 h-[calc(100vh-64px)] flex-1 overflow-y-auto p-8 md:ml-20">{children}</main>
    </>
  );
}
