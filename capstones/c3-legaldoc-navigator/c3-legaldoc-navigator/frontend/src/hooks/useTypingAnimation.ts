import { useEffect, useRef, useState } from "react";

interface UseTypingAnimationOptions {
  enabled?: boolean;
  speedMs?: number;
  onComplete?: () => void;
}

export function useTypingAnimation(
  text: string,
  { enabled = true, speedMs = 10, onComplete }: UseTypingAnimationOptions = {},
) {
  const [displayed, setDisplayed] = useState(enabled ? "" : text);
  const [isTyping, setIsTyping] = useState(enabled);
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  useEffect(() => {
    if (!enabled) {
      setDisplayed(text);
      setIsTyping(false);
      return;
    }

    setDisplayed("");
    setIsTyping(true);
    let index = 0;

    const tick = () => {
      index += 1;
      setDisplayed(text.slice(0, index));

      if (index >= text.length) {
        setIsTyping(false);
        onCompleteRef.current?.();
        return;
      }

      const char = text[index - 1];
      const delay = char === "\n" ? speedMs * 3 : speedMs;
      timerId = window.setTimeout(tick, delay);
    };

    let timerId = window.setTimeout(tick, speedMs);
    return () => window.clearTimeout(timerId);
  }, [text, enabled, speedMs]);

  return { displayed, isTyping };
}
