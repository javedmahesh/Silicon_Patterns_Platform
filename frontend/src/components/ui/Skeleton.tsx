import { cx } from "@/lib/cx";

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("animate-pulse rounded-sm bg-control/70", className)} />;
}

/** A few stacked skeleton lines for panel bodies. */
export function SkeletonLines({ rows = 3, className }: { rows?: number; className?: string }) {
  return (
    <div className={cx("space-y-2", className)}>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className={cx("h-3", i === rows - 1 ? "w-2/3" : "w-full")} />
      ))}
    </div>
  );
}
