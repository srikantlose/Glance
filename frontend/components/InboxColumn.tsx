import { Inbox } from "lucide-react";
import type { InboxMessage } from "@/lib/types";
import { fmtIST, truncate } from "@/lib/format";
import { HoverLens } from "./HoverLens";
import { EmptyState } from "./EmptyState";

export function InboxColumn({ messages }: { messages: InboxMessage[] }) {
  if (messages.length === 0) {
    return <EmptyState icon={Inbox} label="No messages" />;
  }

  return (
    <div className="flex flex-col divide-y divide-border">
      {messages.map((m) => (
        <HoverLens key={m.id} kind="message" message={m}>
          <div className="cursor-default px-3 py-2.5 hover:bg-surface-2">
            <div className="flex items-center justify-between gap-2">
              <span className={`truncate text-sm ${m.unread ? "font-semibold text-text" : "text-muted"}`}>{m.from}</span>
              <span className="shrink-0 text-xs text-muted">{fmtIST(m.date)}</span>
            </div>
            <p className={`truncate text-sm ${m.unread ? "text-text" : "text-muted"}`}>{m.subject}</p>
            <p className="truncate text-xs text-muted">{truncate(m.snippet, 80)}</p>
          </div>
        </HoverLens>
      ))}
    </div>
  );
}
