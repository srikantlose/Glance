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
  target: EntityTarget | null;
  /** target and position frozen at the moment the prompt opened, so moving the mouse
   * while typing can't swap what the instruction lands on. */
  locked: { target: EntityTarget; anchor: Point } | null;
  busy: boolean;
  setBusy: (b: boolean) => void;
  open: () => void;
  close: () => void;
}

const PointerContext = createContext<PointerState | null>(null);

export function usePointer(): PointerState {
  const ctx = useContext(PointerContext);
  if (!ctx) throw new Error("usePointer must be used inside a PointerProvider");
  return ctx;
}

function readTarget(el: Element | null): EntityTarget | null {
  const host = el?.closest<HTMLElement>("[data-glance-kind]");
  if (!host) return null;

  const { glanceKind, glanceId, glanceLabel, glanceEventIds } = host.dataset;
  if (!glanceKind || !glanceId) return null;

  return {
    kind: glanceKind as EntityKind,
    id: glanceId,
    label: glanceLabel ?? "",
    eventIds: glanceEventIds ? glanceEventIds.split(",").filter(Boolean) : undefined,
  };
}

function isTypingInto(el: EventTarget | null): boolean {
  const node = el as HTMLElement | null;
  if (!node) return false;
  return node.tagName === "INPUT" || node.tagName === "TEXTAREA" || node.isContentEditable;
}

export function PointerProvider({ children }: { children: React.ReactNode }) {
  const posRef = useRef<Point>({ x: 0, y: 0 });
  const [target, setTarget] = useState<EntityTarget | null>(null);
  const [locked, setLocked] = useState<{ target: EntityTarget; anchor: Point } | null>(null);
  const [busy, setBusy] = useState(false);

  // the keydown handler needs the current target without being torn down and rebound
  // on every hover change
  const targetRef = useRef<EntityTarget | null>(null);
  targetRef.current = target;

  const close = useCallback(() => {
    setLocked(null);
    setBusy(false);
  }, []);

  const open = useCallback(() => {
    const next = targetRef.current;
    if (!next) return;
    setLocked({ target: next, anchor: { ...posRef.current } });
  }, []);

  useEffect(() => {
    function onMove(e: MouseEvent) {
      posRef.current = { x: e.clientX, y: e.clientY };

      const next = readTarget(e.target as Element | null);
      setTarget((prev) => {
        if (prev?.id === next?.id && prev?.kind === next?.kind) return prev;
        return next;
      });
    }

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        close();
        return;
      }
      // ctrl+space rather than a bare key so the command bar stays typable
      if (e.code === "Space" && e.ctrlKey && !e.altKey && !e.metaKey) {
        if (isTypingInto(e.target) && !targetRef.current) return;
        e.preventDefault();
        open();
      }
    }

    document.addEventListener("mousemove", onMove, { passive: true });
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open, close]);

  const value = useMemo<PointerState>(
    () => ({ posRef, target, locked, busy, setBusy, open, close }),
    [target, locked, busy, open, close],
  );

  return <PointerContext.Provider value={value}>{children}</PointerContext.Provider>;
}
