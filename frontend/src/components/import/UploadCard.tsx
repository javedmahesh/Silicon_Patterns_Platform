import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileSpreadsheet, Upload } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { toast } from "@/components/ui/Toast";
import { apiErrorMessage } from "@/lib/api/client";
import { useUploadImport } from "@/lib/api/queries";
import { humanBytes } from "./importTones";

const XLSX_RE = /\.xlsx$/i;

/** Admin upload → base64 → preview job → navigate to the import detail. */
export function UploadCard() {
  const nav = useNavigate();
  const upload = useUploadImport();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [pickedAt, setPickedAt] = useState<Date | null>(null);

  const valid = file != null && XLSX_RE.test(file.name);

  function pick(f: File | null) {
    setFile(f);
    setPickedAt(f ? new Date() : null);
  }

  function start() {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const content_base64 = String(reader.result).split(",")[1] ?? "";
      upload.mutate(
        { filename: file.name, content_base64 },
        {
          onSuccess: (job) => {
            toast("Preview generated", "positive");
            nav(`/historical-import/${job.import_id}`);
          },
          onError: (e) => toast(apiErrorMessage(e), "danger"),
        },
      );
    };
    reader.onerror = () => toast("Could not read the file", "danger");
    reader.readAsDataURL(file);
  }

  return (
    <div className="panel p-4">
      <div className="flex items-center gap-2 text-13 font-medium text-fg">
        <Upload size={15} className="text-fg-subtle" /> Upload historical export
      </div>
      <p className="mt-1 text-11 text-fg-subtle">
        Excel (.xlsx). Generates a read-only preview — nothing is imported until you review and commit.
      </p>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx"
          className="hidden"
          onChange={(e) => pick(e.target.files?.[0] ?? null)}
        />
        <Button variant="default" size="sm" onClick={() => inputRef.current?.click()}>
          Choose file
        </Button>
        {file && (
          <div className="flex min-w-0 items-center gap-2 text-12">
            <FileSpreadsheet size={14} className="shrink-0 text-fg-subtle" />
            <span className="truncate text-fg">{file.name}</span>
            <span className="shrink-0 text-fg-subtle">· {humanBytes(file.size)}</span>
            {pickedAt && <span className="shrink-0 text-fg-subtle">· {pickedAt.toLocaleTimeString()}</span>}
            <span className={valid ? "shrink-0 text-positive" : "shrink-0 text-danger"}>
              · {valid ? "valid" : "not .xlsx"}
            </span>
          </div>
        )}
        <Button
          variant="primary"
          size="sm"
          className="ml-auto"
          disabled={!valid || upload.isPending}
          onClick={start}
        >
          {upload.isPending ? "Generating…" : "Start preview"}
        </Button>
      </div>
    </div>
  );
}
