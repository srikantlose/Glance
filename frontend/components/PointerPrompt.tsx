"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useSWRConfig } from "swr";
import { usePointer } from "@/lib/pointer";
import { apiFetch, newIdempotencyKey } from "@/lib/api";
import type { CommandResponse, ExecuteResult, SchedulerOption } from "@/lib/types";
import { CommandResult } from "./CommandResult";

const WIDTH = 256;

export function PointerPrompt() {
  const { prompt, pointerRef, closePrompt } = usePointer();
  const { mutate } = useSWRConfig();
  const boxRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<CommandResponse | null>(null);

  const refresh = () => mutate("/api/dashboard");

  // the node stays mounted so the fade/slide transition has something to animate
  useEffect(() => {
    if (prompt) {
      setText("");
      setResult(null);
      const t = setTimeout(() => inputRef.current?.focus(), 50);
      return () => clearTimeout(t);
    }
  }, [prompt]);

  useLayoutEffect(() => {
    if (!prompt || !boxRef.current) return;
    const { x, y } = prompt.anchor;
    const box = boxRef.current;

    let left = x + 10;
    let top = y + 20;
    if (left + WIDTH > window.innerWidth) left = window.innerWidth - WIDTH - 20;
    if (top + box.offsetHeight > window.innerHeight) top = y - box.offsetHeight - 20;

    box.style.left = `${Math.max(8, left)}px`;
    box.style.top = `${Math.max(8, top)}px`;
  }, [prompt, result]);

  async function run() {
    const target = prompt?.target;
    if (!text.trim() || !target) return;
    setBusy(true);
    try {
      const res = await apiFetch<CommandResponse>("/api/command", {
        method: "POST",
        body: JSON.stringify({
          text: text.trim(),
          context: {
            type: "entity",
            kind: target.kind,
            id: target.id,
            label: target.label,
            event_ids: target.eventIds,
          },
        }),
      });
      setResult(res);
      refresh();
    } finally {
      setBusy(false);
    }
  }

  async function clarifyAnswer(clarificationId: string, answer: string, saveAsPolicy: boolean) {
    setBusy(true);
    try {
      const res = await apiFetch<CommandResponse>("/api/clarify", {
        method: "POST",
        body: JSON.stringify({ clarification_id: clarificationId, answer, save_as_policy: saveAsPolicy }),
      });
      setResult(res);
      refresh();
    } finally {
      setBusy(false);
    }
  }

  async function applyOption(option: SchedulerOption) {
    if (!option.descriptor) return;
    setBusy(true);
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
      setBusy(false);
    }
  }

  return (
    <div
      id="pointer-prompt"
      ref={boxRef}
      className={`w-64 rounded-xl bg-surface-charcoal/90 p-3 ${prompt ? "active" : ""}`}
      onKeyDown={(e) => {
        if (e.key === "Escape") closePrompt();
      }}
    >
      <div
        title={prompt?.target.label}
        className="mb-2 truncate text-[10px] font-bold tracking-widest text-primary uppercase"
      >
        on: {prompt?.target.label ?? ""}
      </div>

      {!result && (
        <div className="flex items-center">
          <input
            ref={inputRef}
            autoComplete="off"
            value={text}
            disabled={busy}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                run();
              }
            }}
            placeholder={busy ? "Working…" : "Ask Glance..."}
            className="w-full border-none bg-transparent p-0 text-sm text-white placeholder-on-surface-variant focus:ring-0 focus:outline-none"
          />
        </div>
      )}

      {result && (
        <div className="text-sm">
          <CommandResult result={result} onClarifyAnswer={clarifyAnswer} onApplyOption={applyOption} />
        </div>
      )}
    </div>
  );
}
