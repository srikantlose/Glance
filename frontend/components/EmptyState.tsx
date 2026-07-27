import type { LucideIcon } from "lucide-react";

export function EmptyState({ icon: Icon, label }: { icon: LucideIcon; label: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-10 text-muted">
      <Icon size={22} strokeWidth={1.5} />
      <p className="text-sm">{label}</p>
    </div>
  );
}

export function ErrorStrip({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border border-high/30 bg-high/10 px-3 py-2 text-sm text-high">
      <span>{message}</span>
      {onRetry && (
        <button onClick={onRetry} className="shrink-0 rounded border border-high/40 px-2 py-0.5 text-xs hover:bg-high/20">
          retry
        </button>
      )}
    </div>
  );
}
