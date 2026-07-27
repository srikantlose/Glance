"use client";

import { useState } from "react";
import { Send } from "lucide-react";
import type { CommandResponse, SchedulerOption } from "@/lib/types";

interface Props {
  onSubmit: (text: string) => void;
  loading: boolean;
  result: CommandResponse | null;
  onClarifyAnswer: (clarificationId: string, answer: string, saveAsPolicy: boolean) => void;
  onApplyOption: (option: SchedulerOption) => void;
}

export function CommandBar({ onSubmit, loading, result, onClarifyAnswer, onApplyOption }: Props) {
  const [text, setText] = useState("");
  const [answer, setAnswer] = useState("");
  const [saveAsPolicy, setSaveAsPolicy] = useState(true);

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
          {result.type === "executed" && (
            <div>
              <p className="text-text">{result.summary}</p>
              {result.actions.length > 0 && (
                <ul className="mt-1 space-y-0.5 text-xs text-muted">
                  {result.actions.map((a) => (
                    <li key={a.action_id}>
                      {a.tool}.{a.operation} — {a.status} —{" "}
                      <a href="/audit" className="text-accent hover:underline">
                        view in audit
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {result.type === "clarification" && (
            <div>
              <p className="mb-2 text-text">{result.question}</p>
              <div className="flex flex-wrap items-center gap-2">
                <input
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  placeholder="Your answer…"
                  className="flex-1 rounded border border-border bg-surface px-2 py-1 text-sm outline-none focus:border-accent"
                />
                <label className="flex items-center gap-1 text-xs text-muted">
                  <input type="checkbox" checked={saveAsPolicy} onChange={(e) => setSaveAsPolicy(e.target.checked)} />
                  save as my preference
                </label>
                <button
                  onClick={() => {
                    if (!answer.trim()) return;
                    onClarifyAnswer(result.clarification_id, answer.trim(), saveAsPolicy);
                    setAnswer("");
                  }}
                  className="rounded bg-accent px-2 py-1 text-xs font-medium text-bg"
                >
                  Answer
                </button>
              </div>
            </div>
          )}

          {result.type === "approval_pending" && (
            <p className="text-text">
              Waiting for your approval —{" "}
              <a href="/approvals" className="text-accent hover:underline">
                review it
              </a>
            </p>
          )}

          {result.type === "options" && (
            <div>
              <p className="mb-2 text-text">{result.conflict_summary}</p>
              <div className="flex flex-col gap-2">
                {result.options.map((opt) => (
                  <div key={opt.rank} className="rounded border border-border bg-surface p-2">
                    <p className="text-xs text-muted">
                      #{opt.rank} {opt.action}
                    </p>
                    <p className="text-sm">{opt.justification}</p>
                    {opt.cited_episode_or_policy && (
                      <p className="mt-1 text-xs text-accent">cites: {opt.cited_episode_or_policy}</p>
                    )}
                    {opt.descriptor && (
                      <button
                        onClick={() => onApplyOption(opt)}
                        className="mt-2 rounded bg-accent px-2 py-1 text-xs font-medium text-bg"
                      >
                        Apply
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
