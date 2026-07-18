import { useState } from "react";
import { Link } from "react-router-dom";
import { ChevronDown, ChevronRight, Mail, UserCog, Users } from "lucide-react";

import { ContactDrawer } from "@/components/profile/ContactDrawer";
import { DecisionMakerRow } from "@/components/profile/DecisionMakerRow";
import { RunDmIntelligenceModal } from "@/components/profile/RunDmIntelligenceModal";
import { Pager } from "@/components/data/Pager";
import { FilterBar } from "@/components/shell/FilterBar";
import { PageHeader } from "@/components/shell/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { DebouncedInput } from "@/components/ui/DebouncedInput";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { useAuth } from "@/lib/auth/store";
import { useDecisionMakerCompanies, useDecisionMakers } from "@/lib/api/queries";
import type { DecisionMakerCompany, DecisionMakerOut } from "@/lib/api/types";
import { fmtInt, monogram } from "@/lib/format";

/** One company row that expands to lazily load its decision makers. */
function CompanyGroup({ company }: { company: DecisionMakerCompany }) {
  const [open, setOpen] = useState(false);
  const [contactFor, setContactFor] = useState<DecisionMakerOut | null>(null);
  // This directory shows only decision makers, so people are always fetched senior-scoped.
  const { data, isLoading } = useDecisionMakers(
    { company_domain: company.company_domain, page_size: 200, senior: true },
    { enabled: open },
  );
  const people = data?.items ?? [];

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center gap-3 px-3.5 py-2.5 text-left hover:bg-raised"
      >
        <span className="text-fg-subtle">
          {open ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
        </span>
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md border border-line bg-control text-12 text-fg-muted">
          {monogram(company.company_name, company.company_domain)}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-13 text-fg">{company.company_name}</span>
          <span className="block truncate text-11 text-fg-subtle">{company.company_domain}</span>
        </span>
        <Badge tone="accent">
          {fmtInt(company.senior)} decision {company.senior === 1 ? "maker" : "makers"}
        </Badge>
      </button>

      {open && (
        <div className="border-t border-line/60 bg-base px-3.5 pb-3 pl-12">
          {isLoading ? (
            <div className="flex items-center gap-2 py-3 text-12 text-fg-subtle">
              <Spinner size={14} /> Loading decision makers…
            </div>
          ) : people.length === 0 ? (
            <p className="py-3 text-12 text-fg-subtle">No decision makers found for this company.</p>
          ) : (
            <div className="divide-y divide-line/60">
              {people.map((dm) => (
                <DecisionMakerRow
                  key={dm.id}
                  dm={dm}
                  action={
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setContactFor(dm)}
                      title="Add or edit professional contact details"
                    >
                      <Mail size={13} /> Contact
                    </Button>
                  }
                />
              ))}
            </div>
          )}
          <div className="pt-2">
            <Link
              to={`/companies/${encodeURIComponent(company.company_domain)}`}
              className="text-12 text-accent hover:underline"
            >
              View company profile →
            </Link>
          </div>
        </div>
      )}

      {contactFor && (
        <ContactDrawer dm={contactFor} open onClose={() => setContactFor(null)} />
      )}
    </div>
  );
}

const PAGE_SIZE = 25;

export function DecisionMakersPage() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [runOpen, setRunOpen] = useState(false);
  const { isManager } = useAuth();
  const { data, isLoading, isError, error, refetch } = useDecisionMakerCompanies();

  // The Decision Makers directory consists solely of actual decision makers (CxO /
  // founder / VP / director) — the people the team reaches out to. Companies whose
  // resolved contacts include no decision makers are not listed here.
  const companies = data?.companies ?? [];
  const decisionMakerCompanies = companies.filter((c) => c.senior > 0);
  const totalDecisionMakers = decisionMakerCompanies.reduce((sum, c) => sum + c.senior, 0);

  const needle = q.trim().toLowerCase();
  const filtered = needle
    ? decisionMakerCompanies.filter(
        (c) =>
          c.company_name.toLowerCase().includes(needle) ||
          c.company_domain.toLowerCase().includes(needle),
      )
    : decisionMakerCompanies;

  // Paginate the (client-side) company directory into pages instead of one long scroll.
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pages);
  const pageItems = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);
  const onFilter = (v: string) => {
    setQ(v);
    setPage(1); // a new filter resets to the first page
  };

  return (
    <>
      <PageHeader
        title="Decision makers"
        subtitle={
          data
            ? `${fmtInt(decisionMakerCompanies.length)} companies · ${fmtInt(totalDecisionMakers)} decision makers (CxO / founder / VP / director)`
            : "Decision makers (CxO / founder / VP / director) resolved to each company — the people to reach out to"
        }
        actions={
          // Running the paid Apify engine is a management action — manager+ only
          // (RBAC), mirroring the backend require_manager gate on the endpoint.
          isManager ? (
            <Button variant="primary" size="sm" onClick={() => setRunOpen(true)}>
              <UserCog size={14} /> Run Decision Maker Intelligence
            </Button>
          ) : undefined
        }
      >
        <FilterBar activeCount={needle ? 1 : 0} onClear={() => onFilter("")}>
          <DebouncedInput
            value={q}
            onChange={onFilter}
            placeholder="Filter companies…"
            className="w-64"
          />
        </FilterBar>
      </PageHeader>

      <div className="p-4">
        <div className="panel">
          {isError ? (
            <ErrorState title="Couldn't load decision makers" error={error} onRetry={refetch} />
          ) : isLoading ? (
            <div className="grid place-items-center py-12">
              <Spinner size={18} />
            </div>
          ) : filtered.length === 0 ? (
            <EmptyState
              icon={<Users size={20} />}
              title={needle ? "No companies match" : "No decision makers resolved yet"}
              description="Decision makers (CxO / founder / VP / director) are sourced and resolved to a company by the LinkedIn Scraper. Click a company to see who to reach out to."
            />
          ) : (
            <>
              <div className="divide-y divide-line">
                {pageItems.map((c) => (
                  <CompanyGroup key={c.company_domain} company={c} />
                ))}
              </div>
              <div className="border-t border-line px-2">
                <Pager
                  page={safePage}
                  pages={pages}
                  total={filtered.length}
                  pageSize={PAGE_SIZE}
                  onPage={setPage}
                />
              </div>
            </>
          )}
        </div>
      </div>

      <RunDmIntelligenceModal open={runOpen} onClose={() => setRunOpen(false)} />
    </>
  );
}
