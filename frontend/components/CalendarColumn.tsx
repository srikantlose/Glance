import type { CalendarEvent, ConflictGroup } from "@/lib/types";
import { fmtDayIST, fmtTimeIST } from "@/lib/format";
import { HoverLens } from "./HoverLens";
import { EmptyState } from "./EmptyState";
import { Icon } from "./Icon";

export function CalendarColumn({
  events,
  conflicts,
}: {
  events: CalendarEvent[];
  conflicts: ConflictGroup[];
}) {
  if (events.length === 0) {
    return <EmptyState icon="calendar_today" label="No events this week" />;
  }

  const byDay = new Map<string, CalendarEvent[]>();
  for (const ev of events) {
    const day = fmtDayIST(ev.start);
    if (!byDay.has(day)) byDay.set(day, []);
    byDay.get(day)!.push(ev);
  }

  const conflictByGroup = new Map(conflicts.map((c) => [c.group_id, c]));

  return (
    <>
      {Array.from(byDay.entries()).map(([day, dayEvents]) => (
        <div key={day}>
          <div className="mt-4 mb-2 px-2 text-xs font-semibold tracking-wider text-on-surface-variant uppercase">
            {day}
          </div>
          {dayEvents.map((ev) => {
            const conflicted = !!ev.conflict_group;
            const group = ev.conflict_group ? conflictByGroup.get(ev.conflict_group) : undefined;
            return (
              <HoverLens
                key={ev.id}
                kind="event"
                event={ev}
                hasConflict={conflicted}
                conflictEventIds={group?.event_ids}
              >
                <div
                  className={`glance-row relative mb-1 cursor-pointer overflow-hidden rounded-lg p-3 ${
                    conflicted
                      ? "border-tertiary/40 bg-tertiary/5"
                      : "border-border-glass bg-surface-container-lowest/50"
                  }`}
                >
                  <h3 className="mb-1 text-sm font-semibold text-on-surface">{ev.title}</h3>
                  <p className="text-xs text-on-surface-variant">
                    {fmtTimeIST(ev.start)} – {fmtTimeIST(ev.end)}
                  </p>
                  {ev.external && (
                    <Icon
                      name="language"
                      size={16}
                      className="absolute top-3 right-3 text-on-surface-variant"
                    />
                  )}
                </div>
              </HoverLens>
            );
          })}
        </div>
      ))}
    </>
  );
}
