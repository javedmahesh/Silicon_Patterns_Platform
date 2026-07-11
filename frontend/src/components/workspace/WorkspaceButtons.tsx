import { Eye, Flag, Pin } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { IconButton } from "@/components/ui/IconButton";
import { toast } from "@/components/ui/Toast";
import { useWorkspace } from "@/hooks/useWorkspace";
import { cx } from "@/lib/cx";

interface ActionProps {
  domain: string;
  iconOnly?: boolean;
  size?: "sm" | "md";
}

export function WatchButton({ domain, iconOnly, size = "md" }: ActionProps) {
  const { isWatched, toggleWatch } = useWorkspace();
  const on = isWatched(domain);
  const click = () => {
    toggleWatch(domain);
    toast(on ? "Removed from watchlist" : "Added to watchlist", on ? "default" : "positive");
  };
  if (iconOnly) {
    return (
      <IconButton size={size} active={on} onClick={click} aria-label="Watch" title={on ? "Watching" : "Watch"}>
        <Eye size={15} />
      </IconButton>
    );
  }
  return (
    <Button size={size} onClick={click} className={cx(on && "border-accent/40 text-accent")}>
      <Eye size={14} />
      {on ? "Watching" : "Watch"}
    </Button>
  );
}

export function PinButton({ domain, iconOnly, size = "md" }: ActionProps) {
  const { isPinned, togglePin } = useWorkspace();
  const on = isPinned(domain);
  const click = () => {
    togglePin(domain);
    toast(on ? "Unpinned" : "Pinned", on ? "default" : "positive");
  };
  if (iconOnly) {
    return (
      <IconButton size={size} active={on} onClick={click} aria-label="Pin" title={on ? "Pinned" : "Pin"}>
        <Pin size={15} />
      </IconButton>
    );
  }
  return (
    <Button size={size} onClick={click} className={cx(on && "border-accent/40 text-accent")}>
      <Pin size={14} />
      {on ? "Pinned" : "Pin"}
    </Button>
  );
}

export function FollowUpButton({ domain, iconOnly, size = "md" }: ActionProps) {
  const { hasFollowUp, addFollowUp, removeFollowUp } = useWorkspace();
  const on = hasFollowUp(domain);
  const click = () => {
    if (on) {
      removeFollowUp(domain);
      toast("Removed from follow-ups");
    } else {
      addFollowUp(domain);
      toast("Added to follow-up queue", "positive");
    }
  };
  if (iconOnly) {
    return (
      <IconButton
        size={size}
        active={on}
        onClick={click}
        aria-label="Follow up"
        title={on ? "In follow-up queue" : "Add follow-up"}
      >
        <Flag size={15} />
      </IconButton>
    );
  }
  return (
    <Button size={size} onClick={click} className={cx(on && "border-accent/40 text-accent")}>
      <Flag size={14} />
      {on ? "Following up" : "Follow up"}
    </Button>
  );
}
