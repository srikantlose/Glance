/** the Glance mark: stacked rounded diamonds with a G that doubles as an eye.
 * drawn as vector rather than shipping the render -- at 24px in the nav a raster
 * of that logo turns to mud, and the brushed-silver ramp is the same #e2e8f0 the
 * agent pointer uses, so they read as one family. */
export function GlanceMark({ size = 28, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      role="img"
      aria-label="Glance"
      className={className}
    >
      <defs>
        <linearGradient id="gm-steel" x1="14" y1="8" x2="50" y2="56" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#f8fafc" />
          <stop offset="0.35" stopColor="#cbd5e1" />
          <stop offset="0.62" stopColor="#e2e8f0" />
          <stop offset="1" stopColor="#94a3b8" />
        </linearGradient>
        <linearGradient id="gm-steel-dim" x1="10" y1="14" x2="44" y2="52" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#94a3b8" />
          <stop offset="1" stopColor="#475569" />
        </linearGradient>
      </defs>

      {/* the offset plate behind, which gives the mark its layered look */}
      <g transform="rotate(45 32 32)">
        <rect
          x="12"
          y="12"
          width="40"
          height="40"
          rx="11"
          stroke="url(#gm-steel-dim)"
          strokeWidth="2.5"
          fill="none"
          opacity="0.55"
        />
        <rect
          x="17"
          y="17"
          width="34"
          height="34"
          rx="9"
          stroke="url(#gm-steel)"
          strokeWidth="3"
          fill="none"
        />
      </g>

      {/* the eye/G bowl -- open on the right where the G's terminal would be */}
      <path
        d="M42.5 32c-3.6 5.2-7.2 7.8-10.5 7.8S25.1 37.2 21.5 32c3.6-5.2 7.2-7.8 10.5-7.8"
        stroke="url(#gm-steel)"
        strokeWidth="3.2"
        strokeLinecap="round"
        fill="none"
      />
      {/* the G crossbar, doubling as the pupil's glint */}
      <path
        d="M32 32h8.5"
        stroke="url(#gm-steel)"
        strokeWidth="3.2"
        strokeLinecap="round"
      />
    </svg>
  );
}
