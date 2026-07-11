import { ChevronLeft, ChevronRight } from "lucide-react";

import { IconButton } from "@/components/ui/IconButton";
import { fmtInt } from "@/lib/format";

export function Pager({
  page,
  pages,
  total,
  pageSize,
  onPage,
}: {
  page: number;
  pages: number;
  total: number;
  pageSize: number;
  onPage: (page: number) => void;
}) {
  const from = total > 0 ? (page - 1) * pageSize + 1 : 0;
  const to = Math.min(page * pageSize, total);
  return (
    <div className="flex items-center justify-between gap-3 px-1 py-2 text-12 text-fg-muted">
      <span className="tabular">
        {total > 0 ? `${fmtInt(from)}–${fmtInt(to)} of ${fmtInt(total)}` : "0 results"}
      </span>
      <div className="flex items-center gap-1">
        <IconButton size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)} aria-label="Previous page">
          <ChevronLeft size={15} />
        </IconButton>
        <span className="tabular px-2 text-fg-muted">
          {page} / {Math.max(1, pages)}
        </span>
        <IconButton
          size="sm"
          disabled={page >= pages}
          onClick={() => onPage(page + 1)}
          aria-label="Next page"
        >
          <ChevronRight size={15} />
        </IconButton>
      </div>
    </div>
  );
}
