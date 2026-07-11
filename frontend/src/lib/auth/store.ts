/**
 * Auth session store — the signed-in user + the app's session JWT, persisted to
 * localStorage. Mirrors lib/workspace/store.ts (useSyncExternalStore, no new dep).
 * The token is attached as a Bearer header by lib/api/client.ts.
 */
import { useSyncExternalStore } from "react";

import type { UserOut } from "@/lib/api/types";

const KEY = "sp.auth.v1";

export interface Session {
  token: string | null;
  user: UserOut | null;
  devRole: string; // dev-bypass role selector (admin|manager|member); ignored in prod
}
const EMPTY: Session = { token: null, user: null, devRole: "admin" };

function load(): Session {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return EMPTY;
    const parsed = JSON.parse(raw) as Partial<Session>;
    return {
      token: typeof parsed.token === "string" ? parsed.token : null,
      user: (parsed.user as UserOut | null) ?? null,
      devRole: typeof parsed.devRole === "string" ? parsed.devRole : "admin",
    };
  } catch {
    return EMPTY;
  }
}

let state: Session = load();
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((l) => l());
}
function commit(next: Session) {
  state = next;
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    /* ignore quota / privacy-mode errors */
  }
  emit();
}

export const authStore = {
  subscribe(cb: () => void): () => void {
    listeners.add(cb);
    return () => {
      listeners.delete(cb);
    };
  },
  snapshot(): Session {
    return state;
  },
  token(): string | null {
    return state.token;
  },
  devRole(): string {
    return state.devRole;
  },
  setSession(token: string, user: UserOut) {
    commit({ ...state, token, user });
  },
  setUser(user: UserOut) {
    commit({ ...state, user });
  },
  setDevRole(devRole: string) {
    commit({ ...state, devRole });
  },
  clear() {
    commit({ ...EMPTY, devRole: state.devRole });
  },
};

if (typeof window !== "undefined") {
  window.addEventListener("storage", (e) => {
    if (e.key === KEY) {
      state = load();
      emit();
    }
  });
}

/** Dev bypass — explicit opt-in only (VITE_DEV_AUTH_BYPASS=true), to use the app
 *  without login as a synthetic admin. Deliberately simpler than the backend's
 *  security._bypass_on (which also implicitly turns on when neither SP_API_KEY nor
 *  Microsoft is configured) — the frontend has no reliable way to know whether the
 *  backend it's talking to has Microsoft configured, so it just requires this flag
 *  explicitly rather than trying to infer it. */
export const AUTH_BYPASS = import.meta.env.VITE_DEV_AUTH_BYPASS === "true";

/** React hook over the auth store. */
export function useAuth() {
  const session = useSyncExternalStore(authStore.subscribe, authStore.snapshot, () => EMPTY);
  // Before /auth/me resolves under the bypass, fall back to the selected dev role so the
  // nav and route guards don't briefly flash the wrong permissions.
  const effectiveRole = session.user?.role ?? (AUTH_BYPASS ? session.devRole : undefined);
  return {
    token: session.token,
    user: session.user,
    role: effectiveRole,
    bypass: AUTH_BYPASS,
    devRole: session.devRole,
    isAuthed: Boolean(session.token) || AUTH_BYPASS,
    isSuperAdmin: effectiveRole === "super_admin",
    isAdmin: effectiveRole === "admin" || effectiveRole === "super_admin",
    isManager: effectiveRole === "admin" || effectiveRole === "manager" || effectiveRole === "super_admin",
    setSession: authStore.setSession,
    setUser: authStore.setUser,
    setDevRole: authStore.setDevRole,
    logout: authStore.clear,
  };
}
