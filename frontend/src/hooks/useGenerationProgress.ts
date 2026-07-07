import { useEffect, useState } from "react";

export interface ProgressStep {
  id: string;
  label: string;
}

export const GENERATION_STEPS: ProgressStep[] = [
  { id: "search", label: "Searching documents..." },
  { id: "retrieve", label: "Retrieving legal context..." },
  { id: "analyze", label: "Analyzing clauses..." },
  { id: "strict", label: "Generating Evidence response..." },
  { id: "explain", label: "Preparing Explain response..." },
  { id: "complete", label: "Completed" },
];

const STEP_INTERVAL_MS = 1400;

export function useGenerationProgress(active: boolean) {
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (!active) {
      setCurrentIndex(0);
      return;
    }

    setCurrentIndex(0);
    const interval = window.setInterval(() => {
      setCurrentIndex((prev) => {
        const lastActive = GENERATION_STEPS.length - 2;
        if (prev >= lastActive) return prev;
        return prev + 1;
      });
    }, STEP_INTERVAL_MS);

    return () => window.clearInterval(interval);
  }, [active]);

  const complete = () => setCurrentIndex(GENERATION_STEPS.length - 1);

  return {
    steps: GENERATION_STEPS,
    currentIndex: active ? currentIndex : GENERATION_STEPS.length - 1,
    complete,
  };
}
