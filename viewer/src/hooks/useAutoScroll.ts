import { useRef, useEffect, useCallback, RefObject } from "react";

const MANUAL_SCROLL_PAUSE_MS = 3000;
const THROTTLE_MS = 250;

export const useAutoScroll = (
  containerRef: RefObject<HTMLElement | null>,
  activeSelector: string
): void => {
  const manualScrollUntil = useRef(0);
  const lastScrollTime = useRef(0);

  const onManualScroll = useCallback(() => {
    manualScrollUntil.current = Date.now() + MANUAL_SCROLL_PAUSE_MS;
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    el.addEventListener("wheel", onManualScroll, { passive: true });
    el.addEventListener("touchmove", onManualScroll, { passive: true });

    return () => {
      el.removeEventListener("wheel", onManualScroll);
      el.removeEventListener("touchmove", onManualScroll);
    };
  }, [containerRef, onManualScroll]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const now = Date.now();
    if (now < manualScrollUntil.current) return;
    if (now - lastScrollTime.current < THROTTLE_MS) return;

    const active = el.querySelector(activeSelector);
    if (active) {
      lastScrollTime.current = now;
      active.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  });
};
