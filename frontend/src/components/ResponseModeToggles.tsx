import { useLayoutEffect, useRef, useState } from "react";
import {
  RESPONSE_MODE_DESCRIPTIONS,
  RESPONSE_MODE_LABELS,
  RESPONSE_MODES,
  type ResponseMode,
} from "@/lib/responseModes";

interface ResponseModeTogglesProps {
  activeMode: ResponseMode;
  onModeChange: (mode: ResponseMode) => void;
  disabled?: boolean;
  size?: "sm" | "md";
}

export function ResponseModeToggles({
  activeMode,
  onModeChange,
  disabled = false,
  size = "md",
}: ResponseModeTogglesProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [indicator, setIndicator] = useState({ left: 0, width: 0 });

  const padding = size === "sm" ? "px-3 py-1.5" : "px-4 py-2";
  const textSize = size === "sm" ? "text-xs" : "text-sm";

  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const activeButton = container.querySelector<HTMLButtonElement>(
      `[data-mode="${activeMode}"]`,
    );
    if (!activeButton) return;

    setIndicator({
      left: activeButton.offsetLeft,
      width: activeButton.offsetWidth,
    });
  }, [activeMode, size]);

  return (
    <div
      ref={containerRef}
      className="relative inline-flex flex-wrap gap-0.5 rounded-full border border-slate-200/80 bg-slate-100/80 p-1 dark:border-slate-700/80 dark:bg-slate-800/60"
      role="group"
      aria-label="Response mode"
    >
      <span
        className="pointer-events-none absolute top-1 bottom-1 rounded-full bg-white shadow-sm ring-1 ring-slate-900/5 transition-all duration-300 ease-out dark:bg-slate-700 dark:ring-white/10"
        style={{ left: indicator.left, width: indicator.width }}
        aria-hidden
      />

      {RESPONSE_MODES.map((mode) => {
        const selected = activeMode === mode;
        return (
          <button
            key={mode}
            type="button"
            data-mode={mode}
            disabled={disabled}
            aria-pressed={selected}
            title={RESPONSE_MODE_DESCRIPTIONS[mode]}
            onClick={() => onModeChange(mode)}
            className={`focus-ring relative z-10 rounded-full ${padding} ${textSize} font-medium transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-50 ${
              selected
                ? "text-brand-700 dark:text-brand-200"
                : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
            }`}
          >
            {RESPONSE_MODE_LABELS[mode]}
          </button>
        );
      })}
    </div>
  );
}
