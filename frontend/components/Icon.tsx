interface Props {
  name: string;
  className?: string;
  size?: number;
}

/** material symbols outlined -- the ligature font the design system is drawn against. */
export function Icon({ name, className = "", size }: Props) {
  return (
    <span
      aria-hidden
      className={`material-symbols-outlined ${className}`}
      style={size ? { fontSize: `${size}px` } : undefined}
    >
      {name}
    </span>
  );
}
