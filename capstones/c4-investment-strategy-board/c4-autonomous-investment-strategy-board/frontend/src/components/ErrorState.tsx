import { CircleAlert } from "lucide-react";
import { toErrorMessage } from "@/models/errors";
import { Button } from "./Button";

interface ErrorStateProps {
  error: unknown;
  title?: string;
  onRetry?: () => void;
}

export function ErrorState({
  error,
  title = "Unable to load this screen",
  onRetry,
}: ErrorStateProps) {
  return (
    <div
      className="rounded-lg border border-red-200 bg-red-50 px-4 py-6 text-red-800"
      role="alert"
    >
      <div className="flex items-start gap-3">
        <CircleAlert className="mt-0.5 h-5 w-5 shrink-0" />
        <div>
          <p className="font-medium">{title}</p>
          <p className="mt-1 text-sm">{toErrorMessage(error)}</p>
          {onRetry ? (
            <Button className="mt-4" variant="secondary" onClick={onRetry}>
              Try again
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
