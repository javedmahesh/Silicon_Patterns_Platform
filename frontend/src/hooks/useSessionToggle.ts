import { useCallback, useState } from "react";

/**
 * A boolean open/closed toggle remembered for the browser-tab **session** —
 * survives navigation between pages and a reload, and is cleared when the tab
 * closes. Backed by `sessionStorage` (guarded for private-mode/SSR). Used by
 * collapsible sections so an expanded panel stays expanded as you move around.
 */
export function useSessionToggle(key: string, defaultOpen = false): [boolean, () => void] {
  const storageKey = `sp.collapse.${key}`;
  const [open, setOpen] = useState<boolean>(() => {
    try {
      const raw = sessionStorage.getItem(storageKey);
      return raw === null ? defaultOpen : raw === "1";
    } catch {
      return defaultOpen;
    }
  });
  const toggle = useCallback(() => {
    setOpen((prev) => {
      const next = !prev;
      try {
        sessionStorage.setItem(storageKey, next ? "1" : "0");
      } catch {
        /* private mode — fall back to in-memory state only */
      }
      return next;
    });
  }, [storageKey]);
  return [open, toggle];
}
