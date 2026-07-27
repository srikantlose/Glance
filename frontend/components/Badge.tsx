const TONES = {
  high: "bg-high/15 text-high",
  normal: "bg-normal/15 text-normal",
  low: "bg-low/15 text-low",
  success: "bg-success/15 text-success",
  warn: "bg-warn/15 text-warn",
  accent: "bg-accent/15 text-accent",
  muted: "bg-surface-2 text-muted",
} as const;

export function Badge({ tone, children }: { tone: keyof typeof TONES; children: React.ReactNode }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${TONES[tone]}`}>
      {children}
    </span>
  );
}
