import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

import { cx } from "@/lib/cx";
import { IconButton } from "./IconButton";

export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  width = "max-w-lg",
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  width?: string;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex justify-center overflow-y-auto bg-black/60 p-4 pt-[12vh]"
      onMouseDown={onClose}
    >
      <div
        className={cx("panel h-fit w-full", width)}
        onMouseDown={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="flex h-11 items-center justify-between gap-3 border-b border-line px-4">
          <div className="text-13 font-medium text-fg">{title}</div>
          <IconButton size="sm" onClick={onClose} aria-label="Close">
            <X size={15} />
          </IconButton>
        </div>
        <div className="px-4 py-3.5">{children}</div>
        {footer && (
          <div className="flex justify-end gap-2 border-t border-line px-4 py-3">{footer}</div>
        )}
      </div>
    </div>,
    document.body,
  );
}
