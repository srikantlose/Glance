interface Props {
  title: string;
  id?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}

/** the glass column/card every screen is built out of. */
export function Panel({ title, id, action, children }: Props) {
  return (
    <section
      id={id}
      className="flex h-full flex-col overflow-hidden rounded border border-border-glass bg-surface-charcoal/80 backdrop-blur-sm"
    >
      <div className="sticky top-0 z-10 flex items-center justify-between border-b border-border-glass bg-surface-charcoal/90 p-4">
        <h2 className="font-headline-md text-headline-md text-on-surface">{title}</h2>
        {action}
      </div>
      <div className="flex-1 overflow-y-auto p-2">{children}</div>
    </section>
  );
}
