"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import useSWR from "swr";
import { useSWRConfig } from "swr";
import { apiFetch, newIdempotencyKey } from "@/lib/api";
import type { CalendarEvent, CommandResponse, ExecuteResult, InboxMessage, TaskItem, TriageVerdict } from "@/lib/types";
import { Badge } from "./Badge";
import { PolicyPill } from "./PolicyPill";
import { Icon } from "./Icon";
import { usePointer } from "@/lib/pointer";

type Kind = "message" | "event" | "task";
type ButtonState = "idle" | "loading" | "done" | "queued" | "approval";

interface Props {
  kind: Kind;
  message?: InboxMessage;
  event?: CalendarEvent;
  task?: TaskItem;
  hasConflict?: boolean;
  conflictEventIds?: string[];
  children: React.ReactNode;
}

const PRIORITY_TONE = { high: "high", normal: "normal", low: "low" } as const;

const CARD_W = 288; // w-72
const CARD_H_EST = 200; // enough to decide whether to flip above the row
const MARGIN = 8;

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

export function HoverLens({
  kind,
  message,
  event,
  task,
  hasConflict,
  conflictEventIds,
  children,
}: Props) {
  const [show, setShow] = useState(false);
  const [pos, setPos] = useState<{ left: number; top?: number; bottom?: number } | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const openTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  // the card is portalled but is still a react child of this wrapper, so enter/leave
  // can arrive in either order -- track both regions and decide when the timer fires
  const inside = useRef({ row: false, card: false });
  const [buttonState, setButtonState] = useState<Record<string, ButtonState>>({});
  const [composeOpen, setComposeOpen] = useState<Record<string, boolean>>({});
  const [composeText, setComposeText] = useState<Record<string, string>>({});
  const { mutate } = useSWRConfig();
  const { armed, prompt } = usePointer();

  // the pointer owns the screen once it's armed -- leaving this card up as well just
  // stacks two popovers on the same row
  const suppressed = armed || prompt !== null;

  function place() {
    const el = wrapRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();

    let left = r.right - CARD_W;
    left = Math.min(Math.max(MARGIN, left), window.innerWidth - CARD_W - MARGIN);

    // when it won't fit underneath, anchor the card's BOTTOM to the row's top edge and
    // let it grow upward -- pinning `top` instead needs the height up front, and
    // guessing it left a dead gap between row and card that killed the hover
    if (window.innerHeight - r.bottom < CARD_H_EST + MARGIN) {
      setPos({ left, bottom: window.innerHeight - r.top + 2 });
    } else {
      setPos({ left, top: r.bottom + 2 });
    }
  }

  function scheduleClose() {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    closeTimer.current = setTimeout(() => {
      // decided at fire time, so it doesn't matter which of enter/leave landed first
      if (!inside.current.row && !inside.current.card) setShow(false);
    }, 260);
  }

  function enter(region: "row" | "card") {
    inside.current[region] = true;
    if (closeTimer.current) {
      clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
    if (show || openTimer.current) return;
    openTimer.current = setTimeout(() => {
      openTimer.current = null;
      place();
      setShow(true);
    }, 150);
  }

  function leave(region: "row" | "card") {
    inside.current[region] = false;
    if (openTimer.current) {
      clearTimeout(openTimer.current);
      openTimer.current = null;
    }
    scheduleClose();
  }

  useEffect(() => {
    return () => {
      if (openTimer.current) clearTimeout(openTimer.current);
      if (closeTimer.current) clearTimeout(closeTimer.current);
    };
  }, []);

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
      mutate("/api/dashboard");
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

  async function resolveConflict() {
    if (!conflictEventIds?.length) return;
    setButtonState((s) => ({ ...s, conflict: "loading" }));
    try {
      await apiFetch<CommandResponse>("/api/command", {
        method: "POST",
        body: JSON.stringify({
          text: "Resolve this conflict",
          context: { type: "conflict", event_ids: conflictEventIds },
        }),
      });
      setButtonState((s) => ({ ...s, conflict: "done" }));
    } catch {
      setButtonState((s) => ({ ...s, conflict: "idle" }));
    }
  }

  // the agent pointer reads these off the dom to work out what it's aimed at, which
  // keeps the three column components from having to know it exists
  const entity = message
    ? { id: message.id, label: `${message.from} — ${message.subject}` }
    : event
      ? { id: event.id, label: event.title }
      : task
        ? { id: task.id, label: task.title }
        : null;

  const btn =
    "flex items-center gap-1 rounded border border-border-glass px-2 py-1 text-xs text-on-surface transition-colors hover:bg-surface-container-high disabled:opacity-50";

  const card = (
    <div
      style={{ position: "fixed", left: pos?.left ?? 0, top: pos?.top, bottom: pos?.bottom, width: CARD_W }}
      onMouseEnter={() => enter("card")}
      onMouseLeave={() => leave("card")}
      className="z-[9990] rounded-xl border border-border-glass bg-surface-charcoal/95 p-3 shadow-[0_20px_40px_-10px_rgba(0,0,0,0.6)] backdrop-blur-xl"
    >
          {kind === "message" && message && (
            <>
              {!verdict ? (
                <p className="text-xs text-on-surface-variant">thinking…</p>
              ) : (
                <>
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <Badge tone={PRIORITY_TONE[verdict.priority]}>{verdict.priority}</Badge>
                    <span className="text-xs text-on-surface-variant">
                      {verdict.suggested_action.replace("_", " ")}
                    </span>
                    {verdict.cited_policy_id && (
                      <PolicyPill policyId={verdict.cited_policy_id} policyText={verdict.cited_policy_text} />
                    )}
                  </div>
                  <p className="mb-3 text-xs text-on-surface-variant">{verdict.reasoning}</p>
                </>
              )}
              <div className="flex flex-wrap gap-2">
                <button
                  disabled={buttonState.archive === "loading"}
                  onClick={() =>
                    runExecute(
                      "archive",
                      { tool: "gmail", operation: "archive", params: { message_id: message.id } },
                      authorization,
                    )
                  }
                  className={btn}
                >
                  <Icon name="archive" size={12} /> {actionLabel(buttonState.archive, "Archive")}
                </button>
                <button
                  disabled={buttonState.reply === "loading"}
                  onClick={() => setComposeOpen((s) => ({ ...s, reply: !s.reply }))}
                  className={btn}
                >
                  <Icon name="reply" size={12} /> {actionLabel(buttonState.reply, "Reply")}
                </button>
                <button
                  disabled={buttonState.delegate === "loading"}
                  onClick={() => setComposeOpen((s) => ({ ...s, delegate: !s.delegate }))}
                  className={btn}
                >
                  <Icon name="person_add" size={12} /> {actionLabel(buttonState.delegate, "Delegate")}
                </button>
                <button
                  disabled={buttonState.task === "loading"}
                  onClick={() =>
                    runExecute(
                      "task",
                      {
                        tool: "tasks",
                        operation: "task.create",
                        params: { title: message.subject, notes: message.snippet },
                      },
                      authorization,
                    )
                  }
                  className={btn}
                >
                  <Icon name="checklist" size={12} /> {actionLabel(buttonState.task, "To task")}
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
                    className="rounded border border-border-glass bg-surface-container-lowest/60 px-2 py-1 text-xs text-on-surface outline-none focus:border-primary"
                  />
                  <button
                    onClick={() => {
                      const key = composeOpen.reply ? "reply" : "delegate";
                      runComms(key, key as "reply" | "delegate", message.id, composeText[key] || "");
                    }}
                    className="self-end rounded bg-primary-container px-2 py-1 text-xs font-medium text-on-primary-container"
                  >
                    Send
                  </button>
                </div>
              )}
            </>
          )}

          {kind === "event" && event && (
            <>
              <p className="mb-1 text-sm font-semibold text-on-surface">{event.title}</p>
              <p className="mb-3 text-xs text-on-surface-variant">
                {event.attendees.join(", ") || "no attendees"}
              </p>
              {hasConflict && (
                <button
                  disabled={buttonState.conflict === "loading"}
                  onClick={resolveConflict}
                  className="flex items-center gap-1 rounded border border-tertiary/40 bg-tertiary/10 px-2 py-1 text-xs text-tertiary hover:bg-tertiary/20"
                >
                  <Icon name="merge" size={12} /> {actionLabel(buttonState.conflict, "Resolve conflict")}
                </button>
              )}
            </>
          )}

          {kind === "task" && task && (
            <>
              <p className="mb-3 text-sm font-semibold text-on-surface">{task.title}</p>
              <button
                disabled={buttonState.complete === "loading"}
                onClick={() =>
                  runExecute(
                    "complete",
                    { tool: "tasks", operation: "task.complete", params: { task_id: task.id } },
                    { type: "instruction", ref: "hover complete" },
                  )
                }
                className={btn}
              >
                <Icon name="check_circle" size={12} /> {actionLabel(buttonState.complete, "Complete")}
              </button>
            </>
          )}
    </div>
  );

  return (
    <div
      ref={wrapRef}
      className="relative"
      data-glance-kind={entity ? kind : undefined}
      data-glance-id={entity?.id}
      data-glance-label={entity?.label}
      data-glance-event-ids={kind === "event" && conflictEventIds?.length ? conflictEventIds.join(",") : undefined}
      onMouseEnter={() => enter("row")}
      onMouseLeave={() => leave("row")}
    >
      {children}
      {/* portalled to body so the column's overflow-y-auto can't clip it, which it did
          for every row past the halfway mark */}
      {show && !suppressed && pos && createPortal(card, document.body)}
    </div>
  );
}
