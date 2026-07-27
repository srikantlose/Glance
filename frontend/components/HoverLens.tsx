"use client";

import { useRef, useState } from "react";
import useSWR from "swr";
import { Archive, CheckCircle2, CornerUpLeft, GitMerge, ListChecks, UserPlus } from "lucide-react";
import { apiFetch, newIdempotencyKey } from "@/lib/api";
import type { CalendarEvent, CommandResponse, ExecuteResult, InboxMessage, TaskItem, TriageVerdict } from "@/lib/types";
import { Badge } from "./Badge";
import { PolicyPill } from "./PolicyPill";

type Kind = "message" | "event" | "task";
type ButtonState = "idle" | "loading" | "done" | "queued" | "approval";

interface Props {
  kind: Kind;
  message?: InboxMessage;
  event?: CalendarEvent;
  task?: TaskItem;
  hasConflict?: boolean;
  onResolveConflict?: () => void;
  children: React.ReactNode;
}

const PRIORITY_TONE = { high: "high", normal: "normal", low: "low" } as const;

function actionLabel(state: ButtonState | undefined, fallback: string): string {
  switch (state) {
    case "loading":
      return "Working…";
    case "done":
      return "Done ✓";
    case "queued":
      return "Pending — will retry";
    case "approval":
      return "Sent for approval";
    default:
      return fallback;
  }
}

export function HoverLens({ kind, message, event, task, hasConflict, onResolveConflict, children }: Props) {
  const [show, setShow] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [buttonState, setButtonState] = useState<Record<string, ButtonState>>({});
  const [composeOpen, setComposeOpen] = useState<Record<string, boolean>>({});
  const [composeText, setComposeText] = useState<Record<string, string>>({});

  function handleMouseEnter() {
    timerRef.current = setTimeout(() => setShow(true), 150);
  }

  function handleMouseLeave() {
    if (timerRef.current) clearTimeout(timerRef.current);
    setShow(false);
  }

  const { data: verdict } = useSWR<TriageVerdict>(
    kind === "message" && show && message ? `/api/triage/${message.id}` : null,
    (path: string) => apiFetch<TriageVerdict>(path),
  );

  const authorization = verdict?.cited_policy_id
    ? { type: "policy" as const, ref: verdict.cited_policy_id }
    : { type: "instruction" as const, ref: "hover action" };

  async function runExecute(
    key: string,
    descriptor: { tool: string; operation: string; params: Record<string, unknown> },
    auth: { type: string; ref?: string | null },
  ) {
    setButtonState((s) => ({ ...s, [key]: "loading" }));
    try {
      const result = await apiFetch<ExecuteResult>("/api/actions/execute", {
        method: "POST",
        body: JSON.stringify({ descriptor, authorization: auth, idempotency_key: newIdempotencyKey() }),
      });
      setButtonState((s) => ({
        ...s,
        [key]: result.status === "executed" ? "done" : result.status === "queued" ? "queued" : "approval",
      }));
    } catch {
      setButtonState((s) => ({ ...s, [key]: "idle" }));
    }
  }

  async function runComms(key: string, goal: "reply" | "delegate", messageId: string, instructions: string) {
    setButtonState((s) => ({ ...s, [key]: "loading" }));
    setComposeOpen((s) => ({ ...s, [key]: false }));
    try {
      const result = await apiFetch<CommandResponse>("/api/command", {
        method: "POST",
        body: JSON.stringify({
          text: goal === "delegate" ? "Delegate this email" : "Reply to this email",
          context: { type: "comms", goal, message_id: messageId, instructions: instructions.trim() || null },
        }),
      });
      setButtonState((s) => ({ ...s, [key]: result.type === "approval_pending" ? "approval" : "done" }));
    } catch {
      setButtonState((s) => ({ ...s, [key]: "idle" }));
    }
  }

  return (
    <div className="relative" onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>
      {children}
      {show && (
        <div className="absolute right-0 top-full z-30 mt-1 w-72 rounded-lg border border-border bg-surface-2 p-3 shadow-xl">
          {kind === "message" && message && (
            <>
              {!verdict ? (
                <p className="text-xs text-muted">thinking…</p>
              ) : (
                <>
                  <div className="mb-1 flex flex-wrap items-center gap-2">
                    <Badge tone={PRIORITY_TONE[verdict.priority]}>{verdict.priority}</Badge>
                    <span className="text-xs text-muted">{verdict.suggested_action.replace("_", " ")}</span>
                    {verdict.cited_policy_id && (
                      <PolicyPill policyId={verdict.cited_policy_id} policyText={verdict.cited_policy_text} />
                    )}
                  </div>
                  <p className="mb-3 text-xs text-muted">{verdict.reasoning}</p>
                </>
              )}
              <div className="flex flex-wrap gap-2">
                <button
                  disabled={buttonState.archive === "loading"}
                  onClick={() =>
                    runExecute("archive", { tool: "gmail", operation: "archive", params: { message_id: message.id } }, authorization)
                  }
                  className="flex items-center gap-1 rounded border border-border px-2 py-1 text-xs hover:bg-surface disabled:opacity-50"
                >
                  <Archive size={12} /> {actionLabel(buttonState.archive, "Archive")}
                </button>
                <button
                  disabled={buttonState.reply === "loading"}
                  onClick={() => setComposeOpen((s) => ({ ...s, reply: !s.reply }))}
                  className="flex items-center gap-1 rounded border border-border px-2 py-1 text-xs hover:bg-surface disabled:opacity-50"
                >
                  <CornerUpLeft size={12} /> {actionLabel(buttonState.reply, "Reply")}
                </button>
                <button
                  disabled={buttonState.delegate === "loading"}
                  onClick={() => setComposeOpen((s) => ({ ...s, delegate: !s.delegate }))}
                  className="flex items-center gap-1 rounded border border-border px-2 py-1 text-xs hover:bg-surface disabled:opacity-50"
                >
                  <UserPlus size={12} /> {actionLabel(buttonState.delegate, "Delegate")}
                </button>
                <button
                  disabled={buttonState.task === "loading"}
                  onClick={() =>
                    runExecute(
                      "task",
                      { tool: "tasks", operation: "task.create", params: { title: message.subject, notes: message.snippet } },
                      authorization,
                    )
                  }
                  className="flex items-center gap-1 rounded border border-border px-2 py-1 text-xs hover:bg-surface disabled:opacity-50"
                >
                  <ListChecks size={12} /> {actionLabel(buttonState.task, "To task")}
                </button>
              </div>
              {(composeOpen.reply || composeOpen.delegate) && (
                <div className="mt-2 flex flex-col gap-1">
                  <input
                    autoFocus
                    value={composeText[composeOpen.reply ? "reply" : "delegate"] || ""}
                    onChange={(e) => {
                      const key = composeOpen.reply ? "reply" : "delegate";
                      setComposeText((s) => ({ ...s, [key]: e.target.value }));
                    }}
                    placeholder="Anything to mention? (optional)"
                    className="rounded border border-border bg-surface px-2 py-1 text-xs outline-none focus:border-accent"
                  />
                  <button
                    onClick={() => {
                      const key = composeOpen.reply ? "reply" : "delegate";
                      runComms(key, key as "reply" | "delegate", message.id, composeText[key] || "");
                    }}
                    className="self-end rounded bg-accent px-2 py-1 text-xs font-medium text-bg"
                  >
                    Send
                  </button>
                </div>
              )}
            </>
          )}

          {kind === "event" && event && (
            <>
              <p className="mb-1 text-sm font-medium">{event.title}</p>
              <p className="mb-3 text-xs text-muted">{event.attendees.join(", ") || "no attendees"}</p>
              {hasConflict && (
                <button
                  onClick={onResolveConflict}
                  className="flex items-center gap-1 rounded border border-warn/40 bg-warn/10 px-2 py-1 text-xs text-warn hover:bg-warn/20"
                >
                  <GitMerge size={12} /> Resolve conflict
                </button>
              )}
            </>
          )}

          {kind === "task" && task && (
            <>
              <p className="mb-3 text-sm font-medium">{task.title}</p>
              <button
                disabled={buttonState.complete === "loading"}
                onClick={() =>
                  runExecute(
                    "complete",
                    { tool: "tasks", operation: "task.complete", params: { task_id: task.id } },
                    { type: "instruction", ref: "hover complete" },
                  )
                }
                className="flex items-center gap-1 rounded border border-border px-2 py-1 text-xs hover:bg-surface disabled:opacity-50"
              >
                <CheckCircle2 size={12} /> {actionLabel(buttonState.complete, "Complete")}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
