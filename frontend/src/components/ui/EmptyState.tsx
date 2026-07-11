import type { ReactNode } from "react";

import { cx } from "@/lib/cx";

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: ReactNode;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cx(
        "flex flex-col items-center justify-center gap-2 px-6 py-10 text-center",
        className,
      )}
    >
      {icon && <div className="text-fg-subtle [&>svg]:mx-auto">{icon}</div>}
      <div className="text-13 text-fg">{title}</div>
      {description && <div className="max-w-sm text-12 leading-5 text-fg-subtle">{description}</div>}
      {action && <div className="mt-1">{action}</div>}
    </div>
  );
}

/** Inline error surface for failed queries. */
export function ErrorState({
  title = "Something went wrong",
  error,
  onRetry,
  className,
}: {
  title?: string;
  error?: unknown;
  onRetry?: () => void;
  className?: string;
}) {
  const message =
    error instanceof Error ? error.message : typeof error === "string" ? error : undefined;
  return (
    <div
      className={cx(
        "flex flex-col items-center justify-center gap-2 px-6 py-10 text-center",
        className,
      )}
    >
      <div className="text-13 text-danger">{title}</div>
      {message && <div className="max-w-md text-12 leading-5 text-fg-subtle">{message}</div>}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-1 rounded-md border border-line-strong bg-control px-3 h-7 text-12 text-fg hover:bg-raised"
        >
          Retry
        </button>
      )}
    </div>
  );
}
