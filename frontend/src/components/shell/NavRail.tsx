import { PanelLeft, PanelLeftClose } from "lucide-react";
import { NavLink } from "react-router-dom";

import { IconButton } from "@/components/ui/IconButton";
import { useAuth } from "@/lib/auth/store";
import { cx } from "@/lib/cx";
import { canSeeNavItem, NAV_GROUPS, type NavItem } from "./nav";

function RailItem({ item, collapsed }: { item: NavItem; collapsed: boolean }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.end}
      title={collapsed ? item.label : undefined}
      className={({ isActive }) =>
        cx(
          "relative mx-1.5 flex h-8 items-center rounded-md text-13 transition-colors duration-[var(--dur)]",
          collapsed ? "justify-center px-0" : "gap-2.5 px-2",
          isActive
            ? "bg-accent-weak text-fg"
            : "text-fg-muted hover:bg-raised hover:text-fg",
        )
      }
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <span className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-r bg-accent" />
          )}
          <Icon size={16} className="shrink-0" />
          {!collapsed && <span className="truncate">{item.label}</span>}
        </>
      )}
    </NavLink>
  );
}

export function NavRail({
  collapsed,
  onToggle,
}: {
  collapsed: boolean;
  onToggle: () => void;
}) {
  const { isManager, isAdmin } = useAuth();
  const canSee = (item: NavItem) => canSeeNavItem(item, { isManager, isAdmin });
  return (
    <nav
      className={cx(
        "flex h-full shrink-0 flex-col border-r border-line bg-base transition-[width] duration-150",
        collapsed ? "w-[var(--rail-w-collapsed)]" : "w-[var(--rail-w)]",
      )}
    >
      <div className="flex h-[var(--topbar-h)] shrink-0 items-center gap-2 border-b border-line px-3">
        <div className="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-accent-weak text-13 font-medium text-accent">
          SP
        </div>
        {!collapsed && (
          <div className="truncate text-13 font-medium text-fg">Silicon Patterns</div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto py-2">
        {NAV_GROUPS.map((group) => {
          const items = group.items.filter(canSee);
          if (items.length === 0) return null;
          return (
            <div key={group.label} className="mb-1.5">
              {!collapsed && (
                <div className="px-3 pb-1 pt-2 text-11 uppercase tracking-wide text-fg-subtle">
                  {group.label}
                </div>
              )}
              <div className="flex flex-col gap-0.5">
                {items.map((item) => (
                  <RailItem key={item.to} item={item} collapsed={collapsed} />
                ))}
              </div>
            </div>
          );
        })}
      </div>

      <div className="border-t border-line p-1.5">
        <IconButton onClick={onToggle} aria-label="Toggle sidebar" className="w-full">
          {collapsed ? <PanelLeft size={16} /> : <PanelLeftClose size={16} />}
        </IconButton>
      </div>
    </nav>
  );
}
