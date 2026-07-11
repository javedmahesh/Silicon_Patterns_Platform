import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

import { IconButton } from "@/components/ui/IconButton";
import { cx } from "@/lib/cx";

/** Right-side sheet for triage without leaving the list. */
export function PeekDrawer({
  open,
  onClose,
  title,
  children,
  footer,
  width = 440,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  width?: number;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return createPortal(
    <>
      <div
        className={cx(
          "fixed inset-0 z-40 bg-black/50 transition-opacity duration-150",
          open ? "opacity-100" : "pointer-events-none opacity-0",
        )}
        onClick={onClose}
        aria-hidden
      />
      <aside
        className={cx(
          "fixed inset-y-0 right-0 z-40 flex max-w-[90vw] flex-col border-l border-line bg-surface transition-transform duration-150",
          open ? "translate-x-0" : "translate-x-full",
        )}
        style={{ width }}
        role="dialog"
        aria-modal="true"
        aria-hidden={!open}
      >
        <div className="flex h-[var(--topbar-h)] shrink-0 items-center justify-between gap-3 border-b border-line px-3.5">
          <div className="min-w-0 truncate text-13 font-medium text-fg">{title}</div>
          <IconButton size="sm" onClick={onClose} aria-label="Close">
            <X size={15} />
          </IconButton>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-3.5">{children}</div>
        {footer && <div className="shrink-0 border-t border-line p-3">{footer}</div>}
      </aside>
    </>,
    document.body,
  );
}
