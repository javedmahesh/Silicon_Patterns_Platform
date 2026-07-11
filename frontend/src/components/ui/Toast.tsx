import { useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import { CheckCircle2, Info, XCircle } from "lucide-react";

import { cx } from "@/lib/cx";

type Tone = "default" | "positive" | "danger";
interface ToastItem {
  id: number;
  title: string;
  tone: Tone;
}

let items: ToastItem[] = [];
const subs = new Set<() => void>();
let seq = 1;

function emit() {
  subs.forEach((s) => s());
}

/** Fire a transient toast from anywhere (no provider needed). */
export function toast(title: string, tone: Tone = "default", ttl = 3200) {
  const id = seq++;
  items = [...items, { id, title, tone }];
  emit();
  window.setTimeout(() => {
    items = items.filter((t) => t.id !== id);
    emit();
  }, ttl);
}

const icons: Record<Tone, typeof Info> = {
  default: Info,
  positive: CheckCircle2,
  danger: XCircle,
};

export function Toaster() {
  const snap = useSyncExternalStore(
    (cb) => {
      subs.add(cb);
      return () => subs.delete(cb);
    },
    () => items,
    () => items,
  );

  return createPortal(
    <div className="fixed bottom-4 right-4 z-[100] flex w-[280px] flex-col gap-2">
      {snap.map((t) => {
        const Icon = icons[t.tone];
        return (
          <div
            key={t.id}
            className={cx(
              "panel flex items-start gap-2 px-3 py-2 text-12 text-fg shadow-lg",
              t.tone === "positive" && "border-positive/40",
              t.tone === "danger" && "border-danger/40",
            )}
          >
            <Icon
              size={14}
              className={cx(
                "mt-px shrink-0",
                t.tone === "positive" && "text-positive",
                t.tone === "danger" && "text-danger",
                t.tone === "default" && "text-accent",
              )}
            />
            <span className="leading-4">{t.title}</span>
          </div>
        );
      })}
    </div>,
    document.body,
  );
}
