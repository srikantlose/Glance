import type { TaskItem } from "@/lib/types";
import { fmtIST } from "@/lib/format";
import { HoverLens } from "./HoverLens";
import { EmptyState } from "./EmptyState";

export function TasksColumn({ tasks }: { tasks: TaskItem[] }) {
  if (tasks.length === 0) {
    return <EmptyState icon="assignment" label="No tasks" />;
  }

  return (
    <>
      {tasks.map((t) => (
        <HoverLens key={t.id} kind="task" task={t}>
          <div className="glance-row mb-1 flex cursor-pointer items-start justify-between rounded p-3">
            <div>
              <h3
                className={`mb-1 text-sm font-semibold ${
                  t.status === "completed" ? "text-on-surface-variant line-through" : "text-on-surface"
                }`}
              >
                {t.title}
              </h3>
              {t.due && <p className="text-xs text-on-surface-variant">due {fmtIST(t.due)}</p>}
            </div>
            {t.overdue && (
              <span className="rounded-full border border-error/30 bg-error-container/20 px-2 py-0.5 text-[10px] font-bold tracking-wider text-error">
                overdue
              </span>
            )}
          </div>
        </HoverLens>
      ))}
    </>
  );
}
