import { cx } from "@/lib/cx";
import { gradeVar } from "@/lib/grades";

type Size = "sm" | "md" | "lg";

const dims: Record<Size, string> = {
  sm: "h-5 min-w-[20px] px-1 text-11",
  md: "h-6 min-w-[24px] px-1.5 text-12",
  lg: "h-9 min-w-[40px] px-2 text-18",
};

/** Grade pill colored from the grade tokens (A+ / A / B / C). */
export function GradeBadge({
  grade,
  size = "md",
  className,
}: {
  grade?: string | null;
  size?: Size;
  className?: string;
}) {
  const label = grade && grade.trim() ? grade : "—";
  const c = gradeVar(grade);
  return (
    <span
      className={cx(
        "inline-grid place-items-center rounded-md border font-medium tabular leading-none",
        dims[size],
        className,
      )}
      style={{
        color: c,
        borderColor: `color-mix(in srgb, ${c} 40%, transparent)`,
        background: `color-mix(in srgb, ${c} 12%, transparent)`,
      }}
    >
      {label}
    </span>
  );
}
