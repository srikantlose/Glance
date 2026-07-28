"use client";

import { useState } from "react";
import { Send } from "lucide-react";
import type { CommandResponse, SchedulerOption } from "@/lib/types";
import { CommandResult } from "./CommandResult";

interface Props {
  onSubmit: (text: string) => void;
  loading: boolean;
  result: CommandResponse | null;
  onClarifyAnswer: (clarificationId: string, answer: string, saveAsPolicy: boolean) => void;
  onApplyOption: (option: SchedulerOption) => void;
}

export function CommandBar({ onSubmit, loading, result, onClarifyAnswer, onApplyOption }: Props) {
  const [text, setText] = useState("");

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    onSubmit(text.trim());
    setText("");
  }

  return (
    <div className="border-b border-border bg-surface px-4 py-3">
      <form onSubmit={submit} className="flex gap-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Tell Glance what to do…"
          className="flex-1 rounded-md border border-border bg-surface-2 px-3 py-2 text-sm outline-none focus:border-accent"
        />
        <button
          type="submit"
          disabled={loading}
          className="flex items-center gap-1 rounded-md bg-accent px-3 py-2 text-sm font-medium text-bg disabled:opacity-50"
        >
          <Send size={14} /> {loading ? "Working…" : "Send"}
        </button>
      </form>

      {result && (
        <div className="mt-3 rounded-md border border-border bg-surface-2 p-3 text-sm">
          <CommandResult result={result} onClarifyAnswer={onClarifyAnswer} onApplyOption={onApplyOption} />
        </div>
      )}
    </div>
  );
}
