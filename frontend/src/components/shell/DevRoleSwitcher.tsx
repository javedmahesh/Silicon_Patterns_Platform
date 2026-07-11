import { useQueryClient } from "@tanstack/react-query";
import { FlaskConical } from "lucide-react";

import { api } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth/store";

const ROLES = ["admin", "manager", "member"] as const;

/** Dev-only identity switcher — rendered only under DEV_AUTH_BYPASS. Lets you act as a
 *  synthetic admin / manager / member to validate RBAC without signing in. */
export function DevRoleSwitcher() {
  const { bypass, devRole, setDevRole, setUser } = useAuth();
  const qc = useQueryClient();
  if (!bypass) return null;

  async function pick(role: string) {
    if (role === devRole) return;
    setDevRole(role);
    try {
      setUser(await api.auth.me()); // re-resolve identity with the new X-Dev-Role header
    } catch {
      /* ignore — the invalidate below will retry role-dependent queries */
    }
    qc.invalidateQueries(); // refetch everything under the new identity
  }

  return (
    <label
      className="flex items-center gap-1.5 rounded-md border border-amber-600/50 bg-amber-950/30 px-2 py-1 text-11 text-amber-300"
      title="Developer role switcher — active because DEV_AUTH_BYPASS is on."
    >
      <FlaskConical size={13} />
      <span className="hidden font-medium sm:inline">DEV</span>
      <select
        value={devRole}
        onChange={(e) => pick(e.target.value)}
        className="cursor-pointer bg-transparent text-11 text-amber-200 outline-none"
        aria-label="Developer role"
      >
        {ROLES.map((r) => (
          <option key={r} value={r} className="bg-surface text-fg">
            {r}
          </option>
        ))}
      </select>
    </label>
  );
}
