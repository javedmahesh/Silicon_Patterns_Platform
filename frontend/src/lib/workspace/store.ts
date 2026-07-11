/**
 * Lead Workspace — a tiny localStorage-backed store (no extra dependency) exposed
 * via useSyncExternalStore. Holds the analyst's watchlist, pinned companies, and
 * follow-up queue, all keyed by company_domain. The store API is deliberately
 * decoupled from persistence so a future server-sync backend can replace the
 * localStorage layer without changing any caller.
 */

const KEY = "sp.workspace.v1";

export interface FollowUpItem {
  domain: string;
  note?: string;
  due?: string; // YYYY-MM-DD
  addedAt: string; // ISO
}

export interface WorkspaceState {
  watch: string[];
  pinned: string[];
  followUp: FollowUpItem[];
}

const EMPTY: WorkspaceState = { watch: [], pinned: [], followUp: [] };

function load(): WorkspaceState {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return EMPTY;
    const parsed = JSON.parse(raw) as Partial<WorkspaceState>;
    return {
      watch: Array.isArray(parsed.watch) ? parsed.watch : [],
      pinned: Array.isArray(parsed.pinned) ? parsed.pinned : [],
      followUp: Array.isArray(parsed.followUp) ? parsed.followUp : [],
    };
  } catch {
    return EMPTY;
  }
}

let state: WorkspaceState = load();
const listeners = new Set<() => void>();

function persist() {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    /* ignore quota / privacy-mode errors */
  }
}

function commit(next: WorkspaceState) {
  state = next;
  persist();
  listeners.forEach((l) => l());
}

export function subscribe(cb: () => void): () => void {
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
}

export function getSnapshot(): WorkspaceState {
  return state;
}

// Cross-tab synchronization.
if (typeof window !== "undefined") {
  window.addEventListener("storage", (e) => {
    if (e.key === KEY) {
      state = load();
      listeners.forEach((l) => l());
    }
  });
}

function toggle(list: string[], domain: string): string[] {
  return list.includes(domain) ? list.filter((d) => d !== domain) : [domain, ...list];
}

export const workspace = {
  toggleWatch(domain: string) {
    commit({ ...state, watch: toggle(state.watch, domain) });
  },
  togglePin(domain: string) {
    commit({ ...state, pinned: toggle(state.pinned, domain) });
  },
  addFollowUp(domain: string, note?: string, due?: string) {
    const rest = state.followUp.filter((f) => f.domain !== domain);
    commit({
      ...state,
      followUp: [{ domain, note, due, addedAt: new Date().toISOString() }, ...rest],
    });
  },
  removeFollowUp(domain: string) {
    commit({ ...state, followUp: state.followUp.filter((f) => f.domain !== domain) });
  },
  clearAll() {
    commit(EMPTY);
  },
};
