"use client";

import { useState } from "react";
import { apiFetch, newIdempotencyKey, useDashboard } from "@/lib/api";
import type { CommandResponse, ExecuteResult, SchedulerOption } from "@/lib/types";
import { CommandBar } from "@/components/CommandBar";
import { InboxColumn } from "@/components/InboxColumn";
import { CalendarColumn } from "@/components/CalendarColumn";
import { TasksColumn } from "@/components/TasksColumn";
import { ErrorStrip } from "@/components/EmptyState";

export default function DashboardPage() {
  const { data, error, isLoading, mutate } = useDashboard();
  const [result, setResult] = useState<CommandResponse | null>(null);
  const [loading, setLoading] = useState(false);

  async function submitCommand(text: string, context?: Record<string, unknown>) {
    setLoading(true);
    try {
      const res = await apiFetch<CommandResponse>("/api/command", {
        method: "POST",
        body: JSON.stringify({ text, context }),
      });
      setResult(res);
    } finally {
      setLoading(false);
    }
  }

  async function clarifyAnswer(clarificationId: string, answer: string, saveAsPolicy: boolean) {
    setLoading(true);
    try {
      const res = await apiFetch<CommandResponse>("/api/clarify", {
        method: "POST",
        body: JSON.stringify({ clarification_id: clarificationId, answer, save_as_policy: saveAsPolicy }),
      });
      setResult(res);
    } finally {
      setLoading(false);
    }
  }

  async function applyOption(option: SchedulerOption) {
    if (!option.descriptor) return;
    setLoading(true);
    try {
      const res = await apiFetch<ExecuteResult>("/api/actions/execute", {
        method: "POST",
        body: JSON.stringify({
          descriptor: option.descriptor,
          authorization: { type: "instruction", ref: option.justification },
          idempotency_key: newIdempotencyKey(),
        }),
      });
      setResult({
        type: "executed",
        summary: "Applied: " + option.justification,
        actions: res.action_id
          ? [{ action_id: res.action_id, tool: option.descriptor.tool, operation: option.descriptor.operation, status: res.status }]
          : [],
      });
      mutate();
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-full flex-col">
      <CommandBar
        onSubmit={(text) => submitCommand(text)}
        loading={loading}
        result={result}
        onClarifyAnswer={clarifyAnswer}
        onApplyOption={applyOption}
      />

      <div className="flex-1 p-4">
        {error && <ErrorStrip message="Couldn't reach the backend." onRetry={() => mutate()} />}
        {isLoading && <p className="text-sm text-muted">Loading…</p>}

        {data && (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1.2fr_1fr_0.8fr]">
            <section className="rounded-lg border border-border bg-surface">
              <h2 className="border-b border-border px-3 py-2 text-sm font-semibold">Inbox</h2>
              <InboxColumn messages={data.inbox} />
            </section>

            <section className="rounded-lg border border-border bg-surface py-2">
              <h2 className="border-b border-border px-3 py-2 text-sm font-semibold">Calendar</h2>
              <CalendarColumn
                events={data.events}
                conflicts={data.conflicts}
                onResolveConflict={(eventIds) => {
                  const involved = data.events.filter((e) => eventIds.includes(e.id)).map((e) => e.title);
                  submitCommand(`Resolve the conflict between ${involved.join(" and ")}`, {
                    type: "conflict",
                    event_ids: eventIds,
                  });
                }}
              />
            </section>

            <section className="rounded-lg border border-border bg-surface">
              <h2 className="border-b border-border px-3 py-2 text-sm font-semibold">Tasks</h2>
              <TasksColumn tasks={data.tasks} />
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
