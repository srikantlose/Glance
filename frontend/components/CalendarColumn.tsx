import { CalendarDays, Globe } from "lucide-react";
import type { CalendarEvent, ConflictGroup } from "@/lib/types";
import { fmtDayIST, fmtTimeIST } from "@/lib/format";
import { HoverLens } from "./HoverLens";
import { EmptyState } from "./EmptyState";

export function CalendarColumn({
  events,
  conflicts,
  onResolveConflict,
}: {
  events: CalendarEvent[];
  conflicts: ConflictGroup[];
  onResolveConflict: (eventIds: string[]) => void;
}) {
  if (events.length === 0) {
    return <EmptyState icon={CalendarDays} label="No events this week" />;
  }

  const byDay = new Map<string, CalendarEvent[]>();
  for (const ev of events) {
    const day = fmtDayIST(ev.start);
    if (!byDay.has(day)) byDay.set(day, []);
    byDay.get(day)!.push(ev);
  }

  const conflictByGroup = new Map(conflicts.map((c) => [c.group_id, c]));

  return (
    <div className="flex flex-col gap-4">
      {Array.from(byDay.entries()).map(([day, dayEvents]) => (
        <div key={day}>
          <p className="mb-1 px-3 text-xs font-medium uppercase tracking-wide text-muted">{day}</p>
          <div className="flex flex-col gap-1 px-3">
            {dayEvents.map((ev) => {
              const conflicted = !!ev.conflict_group;
              const group = ev.conflict_group ? conflictByGroup.get(ev.conflict_group) : undefined;
              return (
                <HoverLens
                  key={ev.id}
                  kind="event"
                  event={ev}
                  hasConflict={conflicted}
                  onResolveConflict={() => group && onResolveConflict(group.event_ids)}
                >
                  <div
                    className={`rounded-md border px-2.5 py-1.5 text-sm hover:bg-surface-2 ${
                      conflicted ? "border-warn/50 bg-warn/5" : "border-border"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{ev.title}</span>
                      {ev.external && <Globe size={12} className="shrink-0 text-muted" />}
                    </div>
                    <p className="text-xs text-muted">
                      {fmtTimeIST(ev.start)} – {fmtTimeIST(ev.end)}
                    </p>
                  </div>
                </HoverLens>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
