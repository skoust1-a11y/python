import { useEffect, useRef, type RefObject } from "react";

interface UseAutoScrollOptions {
  dependencies: unknown[];
  behavior?: ScrollBehavior;
  enabled?: boolean;
}

export function useAutoScroll<T extends HTMLElement>(
  options: UseAutoScrollOptions,
): RefObject<T | null> {
  const ref = useRef<T>(null);
  const { dependencies, behavior = "smooth", enabled = true } = options;

  useEffect(() => {
    if (!enabled) return;
    const el = ref.current;
    if (!el) return;

    const frame = requestAnimationFrame(() => {
      el.scrollTo({ top: el.scrollHeight, behavior });
    });
    return () => cancelAnimationFrame(frame);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies);

  return ref;
}
