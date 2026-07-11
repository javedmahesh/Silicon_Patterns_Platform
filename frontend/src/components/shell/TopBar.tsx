import { LogOut, Rows3, Search } from "lucide-react";

import { IconButton } from "@/components/ui/IconButton";
import { Tooltip } from "@/components/ui/Tooltip";
import { api } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth/store";
import { ConnectionBadge } from "./ConnectionBadge";
import { DevRoleSwitcher } from "./DevRoleSwitcher";

export function TopBar({
  onOpenPalette,
  compact,
  onToggleDensity,
}: {
  onOpenPalette: () => void;
  compact: boolean;
  onToggleDensity: () => void;
}) {
  const { user, logout } = useAuth();
  const initials = user ? (user.full_name || user.email).trim().slice(0, 1).toUpperCase() : "";
  // Best-effort: the backend logout call is audit-only (app JWTs are stateless) — it
  // shouldn't block the user from signing out of this app if it fails (offline,
  // expired token).
  const handleLogout = async () => {
    await api.auth.logout().catch(() => {});
    logout();
  };
  return (
    <header className="flex h-[var(--topbar-h)] shrink-0 items-center gap-3 border-b border-line bg-base px-3">
      <button
        type="button"
        onClick={onOpenPalette}
        className="flex h-8 w-full max-w-md items-center gap-2 rounded-md border border-line bg-control px-2.5 text-13 text-fg-subtle transition-colors hover:border-line-strong"
      >
        <Search size={14} />
        <span className="flex-1 text-left">Search companies, people, signals…</span>
        <kbd className="rounded border border-line bg-base px-1.5 py-0.5 text-11 text-fg-subtle">
          ⌘K
        </kbd>
      </button>

      <div className="ml-auto flex items-center gap-1.5">
        <Tooltip side="bottom" label={compact ? "Comfortable rows" : "Compact rows"}>
          <IconButton active={compact} onClick={onToggleDensity} aria-label="Toggle density">
            <Rows3 size={16} />
          </IconButton>
        </Tooltip>
        <ConnectionBadge />
        <DevRoleSwitcher />
        {user && (
          <div className="ml-1 flex items-center gap-2 border-l border-line pl-2">
            <div
              className="grid h-7 w-7 place-items-center rounded-full bg-control text-11 text-fg-muted"
              title={`${user.full_name || user.email} · ${user.role}`}
            >
              {initials}
            </div>
            <span className="hidden max-w-[12rem] truncate text-12 text-fg-muted lg:block">
              {user.full_name || user.email}
            </span>
            <Tooltip side="bottom" label="Sign out">
              <IconButton onClick={handleLogout} aria-label="Sign out">
                <LogOut size={15} />
              </IconButton>
            </Tooltip>
          </div>
        )}
      </div>
    </header>
  );
}
