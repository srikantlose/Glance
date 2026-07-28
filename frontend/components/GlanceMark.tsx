/** the Glance mark: two offset rounded diamonds whose overlap reads as a G, with an
 * eye on the right holding a cursor arrow. drawn as vector because the source render
 * (public/screen.png) is 1024px, has its dark backdrop baked in with no alpha, and
 * carries the wordmark -- none of which survives a 30px nav slot. */
export function GlanceMark({ size = 30, className = "" }: { size?: number; className?: string }) {
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
        <linearGradient id="gm-steel" x1="12" y1="10" x2="52" y2="54" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#f8fafc" />
          <stop offset="0.4" stopColor="#cbd5e1" />
          <stop offset="0.7" stopColor="#e2e8f0" />
          <stop offset="1" stopColor="#8fa0b4" />
        </linearGradient>
        <linearGradient id="gm-dark" x1="14" y1="14" x2="46" y2="50" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#6b7789" />
          <stop offset="1" stopColor="#39414f" />
        </linearGradient>
      </defs>

      {/* back plate, offset up-left */}
      <g transform="rotate(45 26 30)">
        <rect
          x="13"
          y="17"
          width="26"
          height="26"
          rx="7"
          stroke="url(#gm-dark)"
          strokeWidth="3"
          fill="none"
        />
      </g>

      {/* front plate, offset down-right -- the overlap is what reads as the G */}
      <g transform="rotate(45 37 34)">
        <rect
          x="24"
          y="21"
          width="26"
          height="26"
          rx="7"
          stroke="url(#gm-steel)"
          strokeWidth="3.4"
          fill="none"
        />
      </g>

      {/* the eye, sitting over the front plate */}
      <path
        d="M25 34c4.2-6 8.7-9 13-9s8.8 3 13 9c-4.2 6-8.7 9-13 9s-8.8-3-13-9Z"
        stroke="url(#gm-steel)"
        strokeWidth="3"
        strokeLinejoin="round"
        fill="none"
      />
      {/* cursor arrow for a pupil -- the pointer is the whole product idea */}
      <path d="M34 28.5 44 33l-4.2 1.6L38 39l-4-10.5Z" fill="url(#gm-steel)" />
    </svg>
  );
}
