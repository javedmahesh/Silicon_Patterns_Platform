import { useState } from "react";
import { CalendarClock } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { toast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api/client";
import { useUpdateSchedulerConfig } from "@/lib/api/queries";
import type { SchedulerStatusOut } from "@/lib/api/types";

const TIME_INPUT =
  "h-8 w-32 rounded-md border border-line bg-control px-2.5 text-13 text-fg focus:border-accent focus:outline-none";

/** Edit the Standard Run schedule — run times (native time picker), on/off, and the
 *  catch-up grace window. Persisted server-side; the scheduler applies it within a
 *  tick. Seeded from the current status when opened. */
export function EditScheduleModal({
  status,
  onClose,
}: {
  status: SchedulerStatusOut;
  onClose: () => void;
}) {
  const [times, setTimes] = useState<string[]>(
    status.schedule_times.length ? status.schedule_times : ["09:00"],
  );
  const [enabled, setEnabled] = useState<boolean>(status.enabled);
  const [grace, setGrace] = useState<number>(status.grace_minutes || 0);
  const save = useUpdateSchedulerConfig();

  const setTime = (i: number, v: string) => setTimes((t) => t.map((x, j) => (j === i ? v : x)));
  const addTime = () => setTimes((t) => [...t, "12:00"]);
  const removeTime = (i: number) => setTimes((t) => t.filter((_, j) => j !== i));

  const clean = times.map((t) => t.trim()).filter(Boolean);
  const valid = clean.length > 0;

  const submit = () =>
    save.mutate(
      { schedule_times: clean, enabled, grace_minutes: grace },
      {
        onSuccess: () => {
          toast("Schedule updated", "positive");
          onClose();
        },
        onError: (e) => toast(apiErrorMessage(e), "danger"),
      },
    );

  return (
    <Modal
      open
      onClose={onClose}
      title={
        <span className="flex items-center gap-2">
          <CalendarClock size={15} /> Edit schedule
        </span>
      }
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={!valid || save.isPending}>
            {save.isPending ? <Spinner size={13} /> : null}
            Save schedule
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <p className="text-12 text-fg-subtle">
          Times are server-local (24-hour). The scheduler runs the full Standard Run at each time and
          picks up changes within about a minute — no restart needed.
        </p>

        <div className="space-y-2">
          <div className="text-12 text-fg-muted">Run times</div>
          {times.map((t, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                type="time"
                value={t}
                onChange={(e) => setTime(i, e.target.value)}
                className={TIME_INPUT}
                aria-label={`Run time ${i + 1}`}
              />
              <Button size="sm" variant="ghost" onClick={() => removeTime(i)} disabled={times.length <= 1}>
                Remove
              </Button>
            </div>
          ))}
          <Button size="sm" variant="default" onClick={addTime}>+ Add time</Button>
        </div>

        <label className="flex items-center gap-2 text-13 text-fg">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
            className="h-4 w-4 accent-[var(--accent)]"
          />
          Scheduler enabled
        </label>

        <label className="block space-y-1">
          <span className="text-12 text-fg-muted">Catch-up grace (minutes)</span>
          <Input
            type="number"
            min={0}
            value={grace}
            onChange={(e) => setGrace(Math.max(0, Number(e.target.value) || 0))}
            className="w-28"
          />
          <span className="block text-11 text-fg-subtle">
            A run missed while the backend was down still fires if it comes back within this window.
            0 disables catch-up.
          </span>
        </label>
      </div>
    </Modal>
  );
}
