import { EnrollmentTable } from "@/components/campaigns/EnrollmentTable";
import { Pager } from "@/components/data/Pager";
import { FilterBar, FilterSelect } from "@/components/shell/FilterBar";
import { PageHeader } from "@/components/shell/PageHeader";
import { DebouncedInput } from "@/components/ui/DebouncedInput";
import { ErrorState } from "@/components/ui/EmptyState";
import { useEnrollments, useSequences } from "@/lib/api/queries";
import { SEQUENCE_ENROLLMENT_STATUSES } from "@/lib/api/types";
import { useUrlFilters } from "@/hooks/useUrlFilters";
import { enumLabel, fmtInt } from "@/lib/format";

const KEYS = ["page", "status", "sequence_id", "q"] as const;
const STATUS_OPTIONS = SEQUENCE_ENROLLMENT_STATUSES.map((s) => ({ value: s, label: enumLabel(s) }));
const PAGE_SIZE = 25;

export function EnrollmentListPage() {
  const { values, setValue, clear, activeCount } = useUrlFilters(KEYS);
  const page = Math.max(1, Number(values.page) || 1);
  const sequences = useSequences({ limit: 200 });
  const sequenceOptions = (sequences.data?.items ?? []).map((s) => ({ value: String(s.id), label: s.name }));

  const { data, isLoading, isError, error, refetch } = useEnrollments({
    status: values.status || undefined,
    sequence_id: values.sequence_id ? Number(values.sequence_id) : undefined,
    search: values.q || undefined,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  });

  return (
    <>
      <PageHeader title="Enrollments" subtitle={data ? `${fmtInt(data.total)} enrollments` : "Leads progressing through a sequence"} />

      <div className="space-y-4 p-4">
        <FilterBar activeCount={activeCount} onClear={clear}>
          <DebouncedInput value={values.q} onChange={(v) => setValue("q", v)} placeholder="Search company…" className="w-56" />
          <FilterSelect label="All statuses" value={values.status} onChange={(v) => setValue("status", v)} options={STATUS_OPTIONS} />
          <FilterSelect label="All sequences" value={values.sequence_id} onChange={(v) => setValue("sequence_id", v)} options={sequenceOptions} />
        </FilterBar>

        <div className="panel">
          {isError ? (
            <ErrorState title="Couldn't load enrollments" error={error} onRetry={refetch} />
          ) : (
            <EnrollmentTable
              enrollments={data?.items ?? []}
              isLoading={isLoading}
              emptyTitle="No enrollments match"
              emptyDescription="Enroll a campaign member into a sequence from a campaign's Members tab."
            />
          )}
          {data && data.pages > 1 && (
            <div className="border-t border-line px-2">
              <Pager page={page} pages={data.pages} total={data.total} pageSize={data.page_size} onPage={(p) => setValue("page", String(p))} />
            </div>
          )}
        </div>
      </div>
    </>
  );
}
