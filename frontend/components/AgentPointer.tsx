"use client";

import { useEffect, useRef } from "react";
import { usePointer } from "@/lib/pointer";

const FOLLOW = 0.18;
const HINT_OFFSET = 14;

/** a second cursor that shadows the real one. it deliberately lags and catches up --
 * moving in lockstep just reads as a decoration stuck to the system cursor. */
export function AgentPointer() {
  const { posRef, target, locked, busy } = usePointer();
  const dotRef = useRef<HTMLDivElement>(null);
  const selfRef = useRef({ x: 0, y: 0 });
  const started = useRef(false);

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let frame = 0;

    function tick() {
      const goal = posRef.current;
      const self = selfRef.current;

      if (!started.current && (goal.x || goal.y)) {
        // don't sweep in from 0,0 on first movement
        self.x = goal.x;
        self.y = goal.y;
        started.current = true;
      } else if (reduced) {
        self.x = goal.x;
        self.y = goal.y;
      } else {
        self.x += (goal.x - self.x) * FOLLOW;
        self.y += (goal.y - self.y) * FOLLOW;
      }

      if (dotRef.current) {
        dotRef.current.style.transform = `translate3d(${self.x}px, ${self.y}px, 0)`;
      }
      frame = requestAnimationFrame(tick);
    }

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [posRef]);

  const isLocked = !!target;
  const state = busy ? "busy" : isLocked ? "locked" : "idle";

  return (
    <div
      ref={dotRef}
      aria-hidden
      className="pointer-events-none fixed left-0 top-0 z-50 will-change-transform"
    >
      <div className="relative -translate-x-1/2 -translate-y-1/2">
        <div
          className={[
            "rounded-full border-2 transition-[width,height,border-color,background-color] duration-150",
            state === "idle" && "h-2.5 w-2.5 border-muted/70 bg-transparent",
            state === "locked" && "h-4 w-4 border-accent bg-accent/25",
            state === "busy" && "h-4 w-4 animate-ping border-accent bg-accent/40",
          ]
            .filter(Boolean)
            .join(" ")}
        />
        {isLocked && !locked && !busy && (
          <span
            style={{ left: HINT_OFFSET }}
            className="absolute top-1/2 -translate-y-1/2 whitespace-nowrap rounded border border-border bg-surface-2/95 px-1.5 py-0.5 text-[10px] text-muted shadow-lg"
          >
            <kbd className="font-sans text-accent">Ctrl</kbd>
            <span className="mx-0.5">+</span>
            <kbd className="font-sans text-accent">Space</kbd>
            <span className="ml-1">to direct</span>
          </span>
        )}
      </div>
    </div>
  );
}
