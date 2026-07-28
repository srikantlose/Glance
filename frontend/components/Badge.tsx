const TONES = {
  high: "border-error/30 bg-error-container/20 text-error",
  normal: "border-tertiary/30 bg-tertiary/10 text-tertiary",
  low: "border-border-glass bg-surface-container-high/40 text-on-surface-variant",
  success: "border-secondary/30 bg-secondary/10 text-secondary",
  warn: "border-tertiary/30 bg-tertiary/10 text-tertiary",
  accent: "border-primary/30 bg-primary-container/20 text-primary",
  muted: "border-border-glass bg-surface-container-high/40 text-on-surface-variant",
} as const;

export function Badge({ tone, children }: { tone: keyof typeof TONES; children: React.ReactNode }) {
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 text-[10px] font-bold tracking-wider ${TONES[tone]}`}
    >
      {children}
    </span>
  );
}
