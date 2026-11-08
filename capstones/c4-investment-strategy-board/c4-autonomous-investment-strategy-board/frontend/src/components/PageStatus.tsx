import type { ReactNode } from "react";
import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
import { LoadingState } from "./LoadingState";

interface PageStatusProps {
  loading?: boolean;
  loadingLabel?: string;
  error?: unknown;
  errorTitle?: string;
  onRetry?: () => void;
  empty?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: ReactNode;
  children?: ReactNode;
}

export function PageStatus({
  loading = false,
  loadingLabel,
  error,
  errorTitle,
  onRetry,
  empty = false,
  emptyTitle = "Nothing to show yet",
  emptyDescription,
  emptyAction,
  children,
}: PageStatusProps) {
  if (loading) {
    return <LoadingState label={loadingLabel} />;
  }
  if (error) {
    return <ErrorState error={error} title={errorTitle} onRetry={onRetry} />;
  }
  if (empty) {
    return (
      <EmptyState
        title={emptyTitle}
        description={emptyDescription}
        action={emptyAction}
      />
    );
  }
  return <>{children}</>;
}
