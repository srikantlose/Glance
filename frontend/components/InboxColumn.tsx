import type { InboxMessage } from "@/lib/types";
import { fmtIST } from "@/lib/format";
import { HoverLens } from "./HoverLens";
import { EmptyState } from "./EmptyState";

export function InboxColumn({ messages }: { messages: InboxMessage[] }) {
  if (messages.length === 0) {
    return <EmptyState icon="inbox" label="No messages" />;
  }

  return (
    <>
      {messages.map((m) => (
        <HoverLens key={m.id} kind="message" message={m}>
          <div className="glance-row mb-1 cursor-pointer rounded p-3">
            <div className="mb-1 flex items-start justify-between">
              <span
                className={`truncate pr-2 font-medium ${m.unread ? "text-on-surface" : "text-on-surface-variant"}`}
              >
                {m.from}
              </span>
              <span className="whitespace-nowrap text-xs text-on-surface-variant">{fmtIST(m.date)}</span>
            </div>
            <h3 className="mb-1 text-sm font-semibold text-on-surface">{m.subject}</h3>
            <p className="truncate text-xs text-on-surface-variant">{m.snippet}</p>
          </div>
        </HoverLens>
      ))}
    </>
  );
}
