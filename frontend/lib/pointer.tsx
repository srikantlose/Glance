"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { EntityKind, EntityTarget } from "./types";

export interface Point {
  x: number;
  y: number;
}

interface PointerState {
  /** live cursor position. a ref, not state -- mousemove fires far too often to re-render on. */
  posRef: React.RefObject<Point>;
  /** the eased position of the agent pointer itself, written each frame by AgentPointer
   * and read when the prompt needs somewhere to anchor. */
  pointerRef: React.RefObject<Point>;
  /** the element currently locked onto, so the pointer can magnet to its centre. */
  lockedElRef: React.RefObject<Element | null>;
  /** ctrl+space is held down */
  armed: boolean;
  /** armed AND sitting on a row */
  lockedTarget: EntityTarget | null;
  /** open prompt, frozen against the row it was released on */
  prompt: { target: EntityTarget; anchor: Point } | null;
  closePrompt: () => void;
}

const PointerContext = createContext<PointerState | null>(null);

export function usePointer(): PointerState {
  const ctx = useContext(PointerContext);
  if (!ctx) throw new Error("usePointer must be used inside a PointerProvider");
  return ctx;
}

function readTarget(el: Element | null): { target: EntityTarget; el: Element } | null {
  const host = el?.closest<HTMLElement>("[data-glance-kind]");
  if (!host) return null;

  const { glanceKind, glanceId, glanceLabel, glanceEventIds } = host.dataset;
  if (!glanceKind || !glanceId) return null;

  return {
    el: host,
    target: {
      kind: glanceKind as EntityKind,
      id: glanceId,
      label: glanceLabel ?? "",
      eventIds: glanceEventIds ? glanceEventIds.split(",").filter(Boolean) : undefined,
    },
  };
}

export function PointerProvider({ children }: { children: React.ReactNode }) {
  const posRef = useRef<Point>({ x: 0, y: 0 });
  const pointerRef = useRef<Point>({ x: 0, y: 0 });
  const lockedElRef = useRef<Element | null>(null);

  const [armed, setArmed] = useState(false);
  const [lockedTarget, setLockedTarget] = useState<EntityTarget | null>(null);
  const [prompt, setPrompt] = useState<{ target: EntityTarget; anchor: Point } | null>(null);

  // mirrors, so the key handlers can read current values without rebinding every render
  const hoveredRef = useRef<{ target: EntityTarget; el: Element } | null>(null);
  const armedRef = useRef(false);
  const lockedRef = useRef<EntityTarget | null>(null);
  const promptRef = useRef(false);
  lockedRef.current = lockedTarget;
  promptRef.current = prompt !== null;

  const closePrompt = useCallback(() => setPrompt(null), []);

  useEffect(() => {
    function onMove(e: MouseEvent) {
      posRef.current = { x: e.clientX, y: e.clientY };
      const hit = readTarget(e.target as Element | null);
      hoveredRef.current = hit;

      if (promptRef.current) return;

      // while armed the lock follows the cursor from row to row, and drops when you
      // wander off onto empty space
      if (armedRef.current) {
        const next = hit?.target ?? null;
        lockedElRef.current = hit?.el ?? null;
        setLockedTarget((prev) => {
          if (prev?.id === next?.id && prev?.kind === next?.kind) return prev;
          return next;
        });
      }
    }

    function onKeyDown(e: KeyboardEvent) {
      if (e.ctrlKey && e.code === "Space") {
        e.preventDefault();
        if (armedRef.current || promptRef.current) return;
        armedRef.current = true;
        setArmed(true);

        const hit = hoveredRef.current;
        if (hit) {
          lockedElRef.current = hit.el;
          setLockedTarget(hit.target);
        }
      }
    }

    function onKeyUp(e: KeyboardEvent) {
      if (e.code === "Escape" && promptRef.current) {
        setPrompt(null);
        return;
      }

      // releasing either half of the chord commits
      if ((e.code === "Space" || e.key === "Control") && armedRef.current) {
        armedRef.current = false;
        setArmed(false);

        const target = lockedRef.current;
        if (target) {
          setPrompt({ target, anchor: { ...pointerRef.current } });
        }
        lockedElRef.current = null;
        setLockedTarget(null);
      }
    }

    function onKeyDownEscape(e: KeyboardEvent) {
      if (e.key === "Escape" && promptRef.current) setPrompt(null);
    }

    document.addEventListener("mousemove", onMove, { passive: true });
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("keydown", onKeyDownEscape);
    document.addEventListener("keyup", onKeyUp);
    return () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("keydown", onKeyDownEscape);
      document.removeEventListener("keyup", onKeyUp);
    };
  }, []);

  const value = useMemo<PointerState>(
    () => ({ posRef, pointerRef, lockedElRef, armed, lockedTarget, prompt, closePrompt }),
    [armed, lockedTarget, prompt, closePrompt],
  );

  return <PointerContext.Provider value={value}>{children}</PointerContext.Provider>;
}
