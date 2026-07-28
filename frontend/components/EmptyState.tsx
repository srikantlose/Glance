import { Icon } from "./Icon";

export function EmptyState({ icon, label }: { icon: string; label: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-10 text-on-surface-variant">
      <Icon name={icon} size={22} />
      <p className="text-sm">{label}</p>
    </div>
  );
}

export function ErrorStrip({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-error/30 bg-error-container/20 px-3 py-2 text-sm text-error">
      <span>{message}</span>
      {onRetry && (
        <button
          onClick={onRetry}
          className="shrink-0 rounded border border-error/40 px-2 py-0.5 text-xs hover:bg-error/20"
        >
          retry
        </button>
      )}
    </div>
  );
}
