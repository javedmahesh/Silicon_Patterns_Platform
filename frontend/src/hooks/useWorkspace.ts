import { useSyncExternalStore } from "react";

import { getSnapshot, subscribe, workspace } from "@/lib/workspace/store";

/** Reactive view of the Lead Workspace + its mutators. Membership checks derive
 *  from the live snapshot so components re-render on change. */
export function useWorkspace() {
  const state = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  return {
    ...state,
    toggleWatch: workspace.toggleWatch,
    togglePin: workspace.togglePin,
    addFollowUp: workspace.addFollowUp,
    removeFollowUp: workspace.removeFollowUp,
    clearAll: workspace.clearAll,
    isWatched: (domain: string) => state.watch.includes(domain),
    isPinned: (domain: string) => state.pinned.includes(domain),
    hasFollowUp: (domain: string) => state.followUp.some((f) => f.domain === domain),
  };
}
