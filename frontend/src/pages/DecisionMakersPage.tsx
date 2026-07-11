import { useState } from "react";
import { Link } from "react-router-dom";
import { ChevronDown, ChevronRight, Mail, UserCog, Users } from "lucide-react";

import { ContactDrawer } from "@/components/profile/ContactDrawer";
import { DecisionMakerRow } from "@/components/profile/DecisionMakerRow";
import { LeadershipSignalsSection } from "@/components/profile/LeadershipSignalsSection";
import { FilterBar } from "@/components/shell/FilterBar";
import { PageHeader } from "@/components/shell/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { CollapsibleSection } from "@/components/ui/CollapsibleSection";
import { DebouncedInput } from "@/components/ui/DebouncedInput";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { useDecisionMakerCompanies, useDecisionMakers, useLeadershipSignals } from "@/lib/api/queries";
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

export function DecisionMakersPage() {
  const [q, setQ] = useState("");
  const { data, isLoading, isError, error, refetch } = useDecisionMakerCompanies();
  const { data: ldr, isLoading: ldrLoading } = useLeadershipSignals({ page_size: 50 });
  const ldrItems = ldr?.items ?? [];
  const ldrTotal = ldr?.total ?? 0;

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

  return (
    <>
      <PageHeader
        title="Decision makers"
        subtitle={
          data
            ? `${fmtInt(decisionMakerCompanies.length)} companies · ${fmtInt(totalDecisionMakers)} decision makers (CxO / founder / VP / director)`
            : "Decision makers (CxO / founder / VP / director) resolved to each company — the people to reach out to"
        }
      >
        <FilterBar activeCount={needle ? 1 : 0} onClear={() => setQ("")}>
          <DebouncedInput
            value={q}
            onChange={setQ}
            placeholder="Filter companies…"
            className="w-64"
          />
        </FilterBar>
      </PageHeader>

      <div className="p-4 space-y-4">
        <CollapsibleSection
          sessionKey="decision-makers-leadership"
          title="Leadership Signals"
          icon={<UserCog size={15} />}
          count={ldrTotal}
        >
          {ldrLoading ? (
            <div className="flex items-center gap-2 py-1 text-12 text-fg-subtle">
              <Spinner size={14} /> Loading leadership signals…
            </div>
          ) : (
            <LeadershipSignalsSection
              signals={ldrItems}
              groupByCompany
              showCompany
              emptyHint="No director-level+ moves detected yet — these surface as the LinkedIn Scraper sources executives and the Blog Crawler records leadership events."
            />
          )}
        </CollapsibleSection>

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
            <div className="divide-y divide-line">
              {filtered.map((c) => (
                <CompanyGroup key={c.company_domain} company={c} />
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
