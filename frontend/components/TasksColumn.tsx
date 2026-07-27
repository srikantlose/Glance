import { ListChecks } from "lucide-react";
import type { TaskItem } from "@/lib/types";
import { fmtIST } from "@/lib/format";
import { Badge } from "./Badge";
import { HoverLens } from "./HoverLens";
import { EmptyState } from "./EmptyState";

export function TasksColumn({ tasks }: { tasks: TaskItem[] }) {
  if (tasks.length === 0) {
    return <EmptyState icon={ListChecks} label="No tasks" />;
  }

  return (
    <div className="flex flex-col divide-y divide-border">
      {tasks.map((t) => (
        <HoverLens key={t.id} kind="task" task={t}>
          <div className="cursor-default px-3 py-2.5 hover:bg-surface-2">
            <div className="flex items-center justify-between gap-2">
              <span className={`truncate text-sm ${t.status === "completed" ? "text-muted line-through" : "text-text"}`}>
                {t.title}
              </span>
              {t.overdue && <Badge tone="high">overdue</Badge>}
            </div>
            {t.due && <p className="text-xs text-muted">due {fmtIST(t.due)}</p>}
          </div>
        </HoverLens>
      ))}
    </div>
  );
}
