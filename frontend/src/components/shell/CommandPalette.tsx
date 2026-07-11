import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ComponentType,
  type KeyboardEvent as ReactKeyboardEvent,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";
import { Building2, CornerDownLeft, Search } from "lucide-react";

import { GradeBadge } from "@/components/data/GradeBadge";
import { Spinner } from "@/components/ui/Spinner";
import { useAuth } from "@/lib/auth/store";
import { cx } from "@/lib/cx";
import { useGlobalSearch } from "@/lib/search/useGlobalSearch";
import { canSeeNavItem, NAV_ITEMS } from "./nav";

interface Entry {
  id: string;
  group: string;
  icon: ComponentType<{ size?: number | string; className?: string }>;
  label: ReactNode;
  sublabel?: ReactNode;
  trailing?: ReactNode;
  run: () => void;
}

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [term, setTerm] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { q, enabled, companies, isLoading } = useGlobalSearch(term);
  const { isManager, isAdmin } = useAuth();

  useEffect(() => {
    if (!open) return;
    setTerm("");
    setActive(0);
    const id = window.setTimeout(() => inputRef.current?.focus(), 20);
    return () => window.clearTimeout(id);
  }, [open]);

  const entries = useMemo<Entry[]>(() => {
    const go = (to: string) => {
      onClose();
      navigate(to);
    };
    const list: Entry[] = [];
    const t = term.trim().toLowerCase();

    NAV_ITEMS.filter((n) => canSeeNavItem(n, { isManager, isAdmin }))
      .filter((n) => !t || n.label.toLowerCase().includes(t))
      .forEach((n) =>
        list.push({
          id: `nav:${n.to}`,
          group: "Navigate",
          icon: n.icon,
          label: n.label,
          run: () => go(n.to),
        }),
      );

    companies.forEach((c) =>
      list.push({
        id: `co:${c.company_domain}`,
        group: "Companies",
        icon: Building2,
        label: c.company_name || c.company_domain,
        sublabel: c.company_domain,
        trailing: c.grade ? <GradeBadge grade={c.grade} size="sm" /> : undefined,
        run: () => go(`/companies/${encodeURIComponent(c.company_domain)}`),
      }),
    );

    if (enabled) {
      list.push({
        id: "act:companies",
        group: "Scoped search",
        icon: Search,
        label: <>Companies matching “{q}”</>,
        run: () => go(`/companies?q=${encodeURIComponent(q)}`),
      });
    }
    return list;
  }, [term, companies, enabled, q, navigate, onClose]);

  useEffect(() => {
    setActive((a) => Math.min(a, Math.max(0, entries.length - 1)));
  }, [entries.length]);

  if (!open) return null;

  const onKeyDown = (e: ReactKeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, entries.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      entries[active]?.run();
    } else if (e.key === "Escape") {
      e.preventDefault();
      onClose();
    }
  };

  let lastGroup = "";

  return createPortal(
    <div
      className="fixed inset-0 z-[60] flex justify-center bg-black/60 p-4 pt-[12vh]"
      onMouseDown={onClose}
    >
      <div
        className="panel h-fit w-full max-w-xl overflow-hidden"
        onMouseDown={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="flex items-center gap-2 border-b border-line px-3">
          <Search size={16} className="text-fg-subtle" />
          <input
            ref={inputRef}
            value={term}
            onChange={(e) => {
              setTerm(e.target.value);
              setActive(0);
            }}
            onKeyDown={onKeyDown}
            placeholder="Search companies, pages…"
            className="h-11 flex-1 bg-transparent text-15 text-fg placeholder:text-fg-subtle focus:outline-none"
          />
          {isLoading && <Spinner />}
        </div>

        <div className="max-h-[52vh] overflow-y-auto py-1.5">
          {entries.length === 0 ? (
            <div className="px-3 py-8 text-center text-12 text-fg-subtle">
              {enabled
                ? "No matches."
                : "Type at least 2 characters to search companies & pages."}
            </div>
          ) : (
            entries.map((entry, i) => {
              const header = entry.group !== lastGroup ? entry.group : null;
              lastGroup = entry.group;
              const Icon = entry.icon;
              return (
                <div key={entry.id}>
                  {header && (
                    <div className="px-3 pb-1 pt-2 text-11 uppercase tracking-wide text-fg-subtle">
                      {header}
                    </div>
                  )}
                  <button
                    type="button"
                    onMouseEnter={() => setActive(i)}
                    onClick={() => entry.run()}
                    className={cx(
                      "flex w-full items-center gap-2.5 px-3 py-1.5 text-left",
                      i === active ? "bg-accent-weak" : "hover:bg-raised",
                    )}
                  >
                    <Icon size={15} className="shrink-0 text-fg-subtle" />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-13 text-fg">{entry.label}</span>
                      {entry.sublabel && (
                        <span className="block truncate text-11 text-fg-subtle">
                          {entry.sublabel}
                        </span>
                      )}
                    </span>
                    {entry.trailing}
                    {i === active && <CornerDownLeft size={13} className="shrink-0 text-fg-subtle" />}
                  </button>
                </div>
              );
            })
          )}
        </div>

        <div className="flex items-center gap-3 border-t border-line px-3 py-1.5 text-11 text-fg-subtle">
          <span>↑↓ navigate</span>
          <span>⏎ open</span>
          <span>esc close</span>
        </div>
      </div>
    </div>,
    document.body,
  );
}
