"use client";

import { useEffect, useRef } from "react";
import { usePointer } from "@/lib/pointer";

const FOLLOW = 0.18;
const SNAP = 0.1;

/** a second cursor that shadows the real one. it deliberately lags and catches up --
 * moving in lockstep just reads as a decoration stuck to the system cursor. */
export function AgentPointer() {
  const { posRef, pointerRef, lockedElRef, armed, lockedTarget, prompt } = usePointer();
  const dotRef = useRef<HTMLDivElement>(null);
  const chipRef = useRef<HTMLDivElement>(null);
  const started = useRef(false);

  // read inside the raf loop without restarting it every state change
  const modeRef = useRef({ armed: false, locked: false, prompting: false });
  modeRef.current = { armed, locked: lockedTarget !== null, prompting: prompt !== null };

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let frame = 0;

    function tick() {
      const goal = posRef.current;
      const self = pointerRef.current;
      const { armed, locked, prompting } = modeRef.current;

      if (!started.current && (goal.x || goal.y)) {
        // don't sweep in from 0,0 on first movement
        self.x = goal.x;
        self.y = goal.y;
        started.current = true;
      } else if (armed && locked && !prompting && lockedElRef.current) {
        // magnet to the middle of whatever row is locked
        const rect = lockedElRef.current.getBoundingClientRect();
        const tx = rect.left + rect.width / 2;
        const ty = rect.top + rect.height / 2;
        self.x += (tx - self.x) * SNAP;
        self.y += (ty - self.y) * SNAP;
      } else if (reduced) {
        self.x = goal.x;
        self.y = goal.y;
      } else {
        self.x += (goal.x - self.x) * FOLLOW;
        self.y += (goal.y - self.y) * FOLLOW;
      }

      if (dotRef.current) {
        dotRef.current.style.left = `${self.x}px`;
        dotRef.current.style.top = `${self.y}px`;
      }
      if (chipRef.current) {
        chipRef.current.style.left = `${self.x}px`;
        chipRef.current.style.top = `${self.y}px`;
      }
      frame = requestAnimationFrame(tick);
    }

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [posRef, pointerRef, lockedElRef]);

  const locked = lockedTarget !== null;
  const classes = ["", armed ? "active-mode" : "", locked ? "locked" : ""].filter(Boolean).join(" ");

  return (
    <>
      <div id="agent-pointer" ref={dotRef} aria-hidden className={classes} />
      <div
        id="pointer-chip"
        ref={chipRef}
        aria-hidden
        className={`flex items-center rounded border border-border-glass bg-surface-charcoal px-2 py-1 shadow-lg backdrop-blur-md ${
          locked && !prompt ? "visible" : ""
        }`}
      >
        <span className="font-label-sm text-label-sm whitespace-nowrap text-on-surface">Ctrl + Space</span>
      </div>
    </>
  );
}
