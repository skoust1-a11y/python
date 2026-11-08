import { useTypingAnimation } from "@/hooks/useTypingAnimation";

interface TypingTextProps {
  text: string;
  enabled?: boolean;
  speedMs?: number;
  className?: string;
  onComplete?: () => void;
}

export function TypingText({
  text,
  enabled = false,
  speedMs = 10,
  className = "",
  onComplete,
}: TypingTextProps) {
  const { displayed, isTyping } = useTypingAnimation(text, {
    enabled,
    speedMs,
    onComplete,
  });

  const isMarkdown = className.includes("legal-markdown");
  const sharedClass = `whitespace-pre-wrap text-[15px] leading-relaxed text-slate-800 dark:text-slate-100 ${isTyping ? "typing-cursor" : ""} ${className}`;

  if (isMarkdown) {
    return (
      <div className={`legal-markdown-prose max-w-[68ch] animate-fade-in ${sharedClass}`}>
        {displayed}
      </div>
    );
  }

  return <p className={sharedClass}>{displayed}</p>;
}
