"use client";

import { useDashboard } from "@/lib/api";
import { InboxColumn } from "@/components/InboxColumn";
import { CalendarColumn } from "@/components/CalendarColumn";
import { TasksColumn } from "@/components/TasksColumn";
import { ErrorStrip } from "@/components/EmptyState";
import { Panel } from "@/components/Panel";

export default function DashboardPage() {
  const { data, error, isLoading, mutate } = useDashboard();

  return (
    <div className="mx-auto grid h-full max-w-[1800px] grid-cols-1 gap-gutter lg:grid-cols-3">
      {error && (
        <div className="lg:col-span-3">
          <ErrorStrip message="Couldn't reach the backend." onRetry={() => mutate()} />
        </div>
      )}

      <Panel id="inbox" title="Inbox">
        {isLoading && !data ? (
          <p className="p-3 text-xs text-on-surface-variant">Loading…</p>
        ) : (
          <InboxColumn messages={data?.inbox ?? []} />
        )}
      </Panel>

      <Panel id="calendar" title="Calendar">
        {isLoading && !data ? (
          <p className="p-3 text-xs text-on-surface-variant">Loading…</p>
        ) : (
          <CalendarColumn events={data?.events ?? []} conflicts={data?.conflicts ?? []} />
        )}
      </Panel>

      <Panel id="tasks" title="Tasks">
        {isLoading && !data ? (
          <p className="p-3 text-xs text-on-surface-variant">Loading…</p>
        ) : (
          <TasksColumn tasks={data?.tasks ?? []} />
        )}
      </Panel>
    </div>
  );
}
