import type { ReactNode } from "react";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type RowData,
} from "@tanstack/react-table";
import { ChevronDown, ChevronUp } from "lucide-react";

import { cx } from "@/lib/cx";

// Column-level presentation + server-sort hints.
declare module "@tanstack/react-table" {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  interface ColumnMeta<TData extends RowData, TValue> {
    align?: "left" | "right";
    sortField?: string;
    headerClass?: string;
    cellClass?: string;
  }
}

export interface DataTableProps<T> {
  columns: ColumnDef<T, any>[];
  data: T[];
  getRowId?: (row: T, index: number) => string;
  onRowClick?: (row: T) => void;
  isActive?: (row: T) => boolean;
  isLoading?: boolean;
  skeletonRows?: number;
  empty?: ReactNode;
  /** Server-driven sort state + handler (header click calls onSortChange with meta.sortField). */
  sort?: { field: string; dir: "asc" | "desc" };
  onSortChange?: (field: string) => void;
}

export function DataTable<T>({
  columns,
  data,
  getRowId,
  onRowClick,
  isActive,
  isLoading,
  skeletonRows = 12,
  empty,
  sort,
  onSortChange,
}: DataTableProps<T>) {
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getRowId,
    manualSorting: true,
  });
  const leafCount = table.getAllLeafColumns().length;

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-13">
        <thead className="sticky top-0 z-10 bg-canvas">
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id} className="border-b border-line">
              {hg.headers.map((header) => {
                const meta = header.column.columnDef.meta;
                const sortable = Boolean(meta?.sortField && onSortChange);
                const sorted = sort?.field && meta?.sortField === sort.field;
                const content = header.isPlaceholder
                  ? null
                  : flexRender(header.column.columnDef.header, header.getContext());
                return (
                  <th
                    key={header.id}
                    className={cx(
                      "h-8 px-3 text-11 font-medium uppercase tracking-wide text-fg-subtle",
                      meta?.align === "right" ? "text-right" : "text-left",
                      meta?.headerClass,
                    )}
                  >
                    {sortable ? (
                      <button
                        type="button"
                        onClick={() => onSortChange!(meta!.sortField!)}
                        className={cx(
                          "inline-flex items-center gap-1 hover:text-fg",
                          meta?.align === "right" && "flex-row-reverse",
                        )}
                      >
                        {content}
                        {sorted &&
                          (sort!.dir === "asc" ? <ChevronUp size={12} /> : <ChevronDown size={12} />)}
                      </button>
                    ) : (
                      content
                    )}
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        <tbody>
          {isLoading ? (
            Array.from({ length: skeletonRows }).map((_, i) => (
              <tr key={i} className="border-b border-line/60">
                {Array.from({ length: leafCount }).map((__, j) => (
                  <td key={j} className="px-3" style={{ height: "var(--row-h)" }}>
                    <div className="h-3 w-full max-w-[140px] animate-pulse rounded-sm bg-control/60" />
                  </td>
                ))}
              </tr>
            ))
          ) : data.length === 0 ? (
            <tr>
              <td colSpan={leafCount} className="py-12">
                {empty ?? <div className="text-center text-12 text-fg-subtle">No results.</div>}
              </td>
            </tr>
          ) : (
            table.getRowModel().rows.map((row) => (
              <tr
                key={row.id}
                onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                className={cx(
                  "border-b border-line/60 transition-colors",
                  onRowClick && "cursor-pointer",
                  isActive?.(row.original)
                    ? "bg-accent-weak"
                    : onRowClick && "hover:bg-raised",
                )}
              >
                {row.getVisibleCells().map((cell) => {
                  const meta = cell.column.columnDef.meta;
                  return (
                    <td
                      key={cell.id}
                      className={cx(
                        "px-3 align-middle",
                        meta?.align === "right" ? "text-right" : "text-left",
                        meta?.cellClass,
                      )}
                      style={{ height: "var(--row-h)" }}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  );
                })}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
