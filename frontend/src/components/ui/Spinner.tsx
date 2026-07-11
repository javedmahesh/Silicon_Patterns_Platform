import { Loader2 } from "lucide-react";

import { cx } from "@/lib/cx";

export function Spinner({ size = 16, className }: { size?: number; className?: string }) {
  return <Loader2 size={size} className={cx("animate-spin text-fg-subtle", className)} />;
}
