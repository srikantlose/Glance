"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Crosshair } from "lucide-react";
import { usePointer } from "@/lib/pointer";
import type { CommandResponse, EntityTarget, SchedulerOption } from "@/lib/types";
import { CommandResult } from "./CommandResult";

const WIDTH = 320;
const GAP = 18;
const MARGIN = 8;

interface Props {
  onSubmit: (text: string, target: EntityTarget) => Promise<CommandResponse | null>;
  onClarifyAnswer: (clarificationId: string, answer: string, saveAsPolicy: boolean) => void;
  onApplyOption: (option: SchedulerOption) => void;
  result: CommandResponse | null;
  onDismiss: () => void;
}

export function PointerPrompt({ onSubmit, onClarifyAnswer, onApplyOption, result, onDismiss }: Props) {
  const { locked, busy, setBusy, close } = usePointer();
  const [text, setText] = useState("");
  const boxRef = useRef<HTMLDivElement>(null);
  const [placement, setPlacement] = useState({ left: 0, top: 0 });

  // fresh prompt every time it reopens on something new
  useEffect(() => {
    if (locked) setText("");
  }, [locked]);

  useLayoutEffect(() => {
    if (!locked) return;
    const { x, y } = locked.anchor;
    const height = boxRef.current?.offsetHeight ?? 120;

    const flipX = x + GAP + WIDTH + MARGIN > window.innerWidth;
    const flipY = y + GAP + height + MARGIN > window.innerHeight;

    setPlacement({
      left: Math.max(MARGIN, flipX ? x - GAP - WIDTH : x + GAP),
      top: Math.max(MARGIN, flipY ? y - GAP - height : y + GAP),
    });
  }, [locked, result]);

  if (!locked) return null;

  async function run() {
    if (!text.trim() || !locked) return;
    setBusy(true);
    try {
      await onSubmit(text.trim(), locked.target);
    } finally {
      setBusy(false);
    }
  }

  function dismiss() {
    onDismiss();
    close();
  }

  return (
    <div
      ref={boxRef}
      style={{ left: placement.left, top: placement.top, width: WIDTH }}
      className="fixed z-40 rounded-lg border border-accent/40 bg-surface-2 p-3 text-sm shadow-2xl"
    >
      <div className="mb-2 flex items-center gap-1.5 text-xs text-muted">
        <Crosshair size={12} className="shrink-0 text-accent" />
        <span className="truncate" title={locked.target.label}>
          {locked.target.label || locked.target.kind}
        </span>
      </div>

      {!result && (
        <input
          autoFocus
          value={text}
          disabled={busy}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              run();
            }
          }}
          placeholder={busy ? "Working…" : "Tell it what to do…"}
          className="w-full rounded border border-border bg-surface px-2 py-1.5 text-sm outline-none focus:border-accent disabled:opacity-60"
        />
      )}

      {result && <CommandResult result={result} onClarifyAnswer={onClarifyAnswer} onApplyOption={onApplyOption} />}

      <button
        onClick={dismiss}
        className="mt-2 text-[10px] text-muted hover:text-text"
      >
        Esc to close
      </button>
    </div>
  );
}
