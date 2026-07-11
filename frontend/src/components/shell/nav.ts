import {
  BarChart3,
  Briefcase,
  Building2,
  CalendarClock,
  CheckSquare,
  ClipboardList,
  FileText,
  Handshake,
  HeartPulse,
  Inbox,
  KanbanSquare,
  LayoutDashboard,
  ListChecks,
  ListOrdered,
  Megaphone,
  Send,
  Settings,
  ShieldCheck,
  Star,
  Target,
  UserCog,
  Users,
  Workflow,
} from "lucide-react";
import type { ComponentType } from "react";

export interface NavItem {
  label: string;
  to: string;
  icon: ComponentType<{ size?: number | string; className?: string }>;
  /** Exact-match routing (only the Dashboard "/" needs this). */
  end?: boolean;
  /** Minimum role to see this item (omitted = visible to everyone). */
  role?: "manager" | "admin";
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

/** The five workbench groups (P6 §1/§3). Company Profile is reached via Companies. */
export const NAV_GROUPS: NavGroup[] = [
  {
    label: "Triage",
    items: [
      { label: "Dashboard", to: "/", icon: LayoutDashboard, end: true },
      { label: "Lead rankings", to: "/leads", icon: ListOrdered },
      { label: "Workspace", to: "/workspace", icon: Star },
      { label: "My leads", to: "/my-leads", icon: ClipboardList },
    ],
  },
  {
    label: "Universe",
    items: [{ label: "Companies", to: "/companies", icon: Building2 }],
  },
  {
    label: "Signals",
    items: [
      { label: "Opportunities", to: "/opportunities", icon: Megaphone },
      { label: "Decision makers", to: "/decision-makers", icon: Users },
    ],
  },
  {
    label: "Intelligence",
    items: [{ label: "Analytics", to: "/analytics", icon: BarChart3 }],
  },
  {
    label: "System",
    items: [
      { label: "Review queue", to: "/review-queue", icon: ShieldCheck },
      { label: "Scheduler", to: "/scheduler", icon: CalendarClock },
      { label: "Team", to: "/team", icon: UserCog, role: "manager" },
      { label: "Administration", to: "/administration", icon: Settings, role: "admin" },
    ],
  },
  {
    // Enterprise CRM Phase 1 — campaigns group leads/DMs into a goal, sequences
    // drive the touches, enrollments track lead progress through a sequence.
    label: "Campaigns",
    items: [
      { label: "Campaigns", to: "/campaigns", icon: Target, end: true },
      { label: "Sequences", to: "/campaigns/sequences", icon: Workflow },
      { label: "Enrollments", to: "/campaigns/enrollments", icon: ListChecks },
    ],
  },
  {
    // Enterprise CRM Phase 2 — deals move through a configurable pipeline of
    // stages; distinct from the Outreach module's own lead-stage Kanban below.
    label: "Deals",
    items: [
      { label: "Pipeline", to: "/deals", icon: KanbanSquare, end: true },
      { label: "Deal list", to: "/deals/list", icon: Handshake },
      { label: "Analytics", to: "/deals/analytics", icon: BarChart3 },
    ],
  },
  {
    // Enterprise CRM Phase 4 — customer accounts post-sale: health, contracts/
    // renewals, success plans, and risk tracking.
    label: "Customer Success",
    items: [
      { label: "Dashboard", to: "/customer-success", icon: HeartPulse, end: true },
      { label: "Accounts", to: "/customer-success/accounts", icon: Briefcase },
      { label: "Renewals", to: "/customer-success/renewals", icon: CalendarClock },
    ],
  },
  {
    // Outreach is a native module on the platform stack (FastAPI + this SPA),
    // reusing companies / decision makers / lead scores / engagement + platform auth.
    label: "Outreach",
    items: [
      { label: "Overview", to: "/outreach", icon: Send, end: true },
      { label: "Leads", to: "/outreach/leads", icon: Users },
      { label: "Pipeline", to: "/outreach/pipeline", icon: KanbanSquare },
      { label: "Tasks", to: "/outreach/tasks", icon: CheckSquare },
      { label: "Approvals", to: "/outreach/approvals", icon: CheckSquare },
      { label: "Templates", to: "/outreach/templates", icon: FileText },
      { label: "Inbox", to: "/outreach/inbox", icon: Inbox },
    ],
  },
];

export const NAV_ITEMS: NavItem[] = NAV_GROUPS.flatMap((g) => g.items);

/** Shared role gate — used by both the nav rail and the command palette so
 *  role-restricted pages (Team, Administration) never leak into either. */
export function canSeeNavItem(item: NavItem, auth: { isManager: boolean; isAdmin: boolean }): boolean {
  return !item.role || (item.role === "manager" ? auth.isManager : auth.isAdmin);
}
