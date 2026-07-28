"use client";

import { useState } from "react";
import type { CommandResponse, SchedulerOption } from "@/lib/types";

interface Props {
  result: CommandResponse;
  onClarifyAnswer: (clarificationId: string, answer: string, saveAsPolicy: boolean) => void;
  onApplyOption: (option: SchedulerOption) => void;
}

/** shared by the nav command bar and the pointer prompt so the clarify/options flows
 * behave identically wherever you started the instruction from. */
export function CommandResult({ result, onClarifyAnswer, onApplyOption }: Props) {
  const [answer, setAnswer] = useState("");
  const [saveAsPolicy, setSaveAsPolicy] = useState(true);

  return (
    <>
      {result.type === "executed" && (
        <div>
          <p className="text-on-surface">{result.summary}</p>
          {result.actions.length > 0 && (
            <ul className="mt-1 space-y-0.5 text-xs text-on-surface-variant">
              {result.actions.map((a) => (
                <li key={a.action_id}>
                  {a.tool}.{a.operation} — {a.status} —{" "}
                  <a href="/audit" className="text-primary hover:underline">
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
          <p className="mb-2 text-on-surface">{result.question}</p>
          <div className="flex flex-wrap items-center gap-2">
            <input
              autoFocus
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && answer.trim()) {
                  e.preventDefault();
                  onClarifyAnswer(result.clarification_id, answer.trim(), saveAsPolicy);
                  setAnswer("");
                }
              }}
              placeholder="Your answer…"
              className="w-full flex-1 rounded border border-border-glass bg-surface-container-lowest/60 px-2 py-1 text-sm text-on-surface outline-none focus:border-primary"
            />
            <label className="flex items-center gap-1 text-xs text-on-surface-variant">
              <input
                type="checkbox"
                checked={saveAsPolicy}
                onChange={(e) => setSaveAsPolicy(e.target.checked)}
              />
              save as my preference
            </label>
            <button
              onClick={() => {
                if (!answer.trim()) return;
                onClarifyAnswer(result.clarification_id, answer.trim(), saveAsPolicy);
                setAnswer("");
              }}
              className="rounded bg-primary-container px-2 py-1 text-xs font-medium text-on-primary-container"
            >
              Answer
            </button>
          </div>
        </div>
      )}

      {result.type === "approval_pending" && (
        <p className="text-on-surface">
          Waiting for your approval —{" "}
          <a href="/approvals" className="text-primary hover:underline">
            review it
          </a>
        </p>
      )}

      {result.type === "options" && (
        <div>
          <p className="mb-2 text-on-surface">{result.conflict_summary}</p>
          <div className="flex flex-col gap-2">
            {result.options.map((opt) => (
              <div
                key={opt.rank}
                className="rounded border border-border-glass bg-surface-container-lowest/50 p-2"
              >
                <p className="font-label-md text-label-md text-on-surface-variant uppercase">
                  #{opt.rank} {opt.action}
                </p>
                <p className="text-sm text-on-surface">{opt.justification}</p>
                {opt.cited_episode_or_policy && (
                  <p className="mt-1 text-xs text-primary">cites: {opt.cited_episode_or_policy}</p>
                )}
                {opt.descriptor && (
                  <button
                    onClick={() => onApplyOption(opt)}
                    className="mt-2 rounded bg-primary-container px-2 py-1 text-xs font-medium text-on-primary-container"
                  >
                    Apply
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
