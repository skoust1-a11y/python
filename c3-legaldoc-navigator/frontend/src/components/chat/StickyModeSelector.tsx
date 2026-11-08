import { useEffect, useRef, useState } from "react";
import { ResponseModeToggles } from "@/components/ResponseModeToggles";
import type { ResponseMode } from "@/lib/responseModes";

const CHAT_SCROLL_SELECTOR = "[data-chat-scroll]";

interface StickyModeSelectorProps {
  activeMode: ResponseMode;
  onModeChange: (mode: ResponseMode) => void;
  disabled?: boolean;
}

export function StickyModeSelector({
  activeMode,
  onModeChange,
  disabled = false,
}: StickyModeSelectorProps) {
  const sentinelRef = useRef<HTMLDivElement>(null);
  const [isStuck, setIsStuck] = useState(false);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const scrollRoot = sentinel.closest(CHAT_SCROLL_SELECTOR);
    const observer = new IntersectionObserver(
      ([entry]) => setIsStuck(!entry.isIntersecting),
      { root: scrollRoot, threshold: 0 },
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, []);

  return (
    <>
      <div ref={sentinelRef} className="pointer-events-none h-px w-full" aria-hidden />
      <div
        className={`sticky top-0 z-20 -mx-1 px-1 transition-[box-shadow,border-color,background-color] duration-200 ${
          isStuck
            ? "border-b border-slate-200/80 bg-slate-50/95 py-2 shadow-sm backdrop-blur-sm dark:border-slate-700/80 dark:bg-slate-950/95"
            : "pb-2"
        }`}
      >
        <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
          Response mode
        </p>
        <ResponseModeToggles
          activeMode={activeMode}
          onModeChange={onModeChange}
          disabled={disabled}
          size="sm"
        />
      </div>
    </>
  );
}
