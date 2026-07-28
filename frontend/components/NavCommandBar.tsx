"use client";

import { useState } from "react";
import { useSWRConfig } from "swr";
import { apiFetch, newIdempotencyKey } from "@/lib/api";
import type { CommandResponse, ExecuteResult, SchedulerOption } from "@/lib/types";
import { CommandResult } from "./CommandResult";
import { Icon } from "./Icon";

/** lives in the top nav, so it owns its own state and refreshes the dashboard through
 * swr's global mutate rather than a callback threaded down from the page. */
export function NavCommandBar() {
  const { mutate } = useSWRConfig();
  const [text, setText] = useState("");
  const [result, setResult] = useState<CommandResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = () => mutate("/api/dashboard");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setLoading(true);
    try {
      const res = await apiFetch<CommandResponse>("/api/command", {
        method: "POST",
        body: JSON.stringify({ text: text.trim() }),
      });
      setResult(res);
      setText("");
      refresh();
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
      refresh();
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
          ? [
              {
                action_id: res.action_id,
                tool: option.descriptor.tool,
                operation: option.descriptor.operation,
                status: res.status,
              },
            ]
          : [],
      });
      refresh();
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative w-full">
      <form
        onSubmit={submit}
        className="relative flex h-10 w-full items-center rounded-lg border border-border-glass bg-surface-charcoal/80 backdrop-blur-sm transition-colors focus-within:border-primary"
      >
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Tell Glance what to do..."
          className="w-full border-none bg-transparent px-4 text-sm text-on-surface placeholder-on-surface-variant focus:ring-0 focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading}
          className="mr-1 flex items-center gap-1 rounded-md bg-surface-container-highest px-4 py-1.5 text-sm font-medium text-on-surface transition-colors hover:bg-surface-container-high disabled:opacity-50"
        >
          <Icon name="send" size={16} /> {loading ? "Working…" : "Send"}
        </button>
      </form>

      {result && (
        <div className="absolute top-12 right-0 left-0 z-50 rounded-xl border border-border-glass bg-surface-charcoal/90 p-3 text-sm shadow-[0_20px_40px_-10px_rgba(0,0,0,0.6)] backdrop-blur-xl">
          <button
            onClick={() => setResult(null)}
            className="float-right -mt-1 text-on-surface-variant hover:text-on-surface"
          >
            <Icon name="close" size={16} />
          </button>
          <CommandResult result={result} onClarifyAnswer={clarifyAnswer} onApplyOption={applyOption} />
        </div>
      )}
    </div>
  );
}
