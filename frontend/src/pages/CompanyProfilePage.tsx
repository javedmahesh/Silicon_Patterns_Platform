import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Activity,
  ArrowLeft,
  Award,
  Building2,
  ClipboardCheck,
  ExternalLink,
  Gauge,
  Info,
  Lightbulb,
  Mail,
  Megaphone,
  UserCog,
  UserPlus,
  Users,
} from "lucide-react";

import { DataCoverage } from "@/components/profile/DataCoverage";
import { ContactDrawer } from "@/components/profile/ContactDrawer";
import { CompanyContactsSection } from "@/components/profile/CompanyContactsSection";
import { CompanyIntelligencePanel } from "@/components/profile/CompanyIntelligencePanel";
import { CompanyRelationshipsPanel } from "@/components/profile/CompanyRelationshipsPanel";
import { DecisionMakerRow } from "@/components/profile/DecisionMakerRow";
import { EngagementStrategy } from "@/components/profile/EngagementStrategy";
import { KeyValueGrid, type KVItem } from "@/components/profile/KeyValueGrid";
import { LeadReviewPanel } from "@/components/profile/LeadReviewPanel";
import { LeadershipSignalsSection } from "@/components/profile/LeadershipSignalsSection";
import { OpportunityRow } from "@/components/profile/OpportunityRow";
import { ProfileHeader } from "@/components/profile/ProfileHeader";
import { RecognitionCard } from "@/components/profile/RecognitionCard";
import { SignalTimeline } from "@/components/profile/SignalTimeline";
import { CompanyCrmPanel } from "@/components/crm/CompanyCrmPanel";
import { ScoreExplanation } from "@/components/score/ScoreExplanation";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { CollapsibleSection } from "@/components/ui/CollapsibleSection";
import { SectionPanel } from "@/components/ui/SectionPanel";
import { Skeleton, SkeletonLines } from "@/components/ui/Skeleton";
import { Button } from "@/components/ui/Button";
import { Tabs, type TabDef } from "@/components/ui/Tabs";
import { ApiError } from "@/lib/api/client";
import { useCompanyProfile } from "@/lib/api/queries";
import type { CompanyProfile, DecisionMakerOut } from "@/lib/api/types";
import { domainHref, enumLabel, fmtScore } from "@/lib/format";

type TabId = "overview" | "score" | "opportunities" | "people" | "intelligence" | "relationships" | "timeline" | "crm";

function PeopleEmpty() {
  return (
    <EmptyState
      icon={<UserPlus size={20} />}
      title="No decision makers resolved"
      description="The LinkedIn Scraper hasn't resolved any contacts to this company yet. Run the LinkedIn integration to source decision makers."
    />
  );
}

/** Decision-maker rows with a per-person Contact action + shared contact drawer. */
function PeopleList({ people }: { people: DecisionMakerOut[] }) {
  const [contactFor, setContactFor] = useState<DecisionMakerOut | null>(null);
  return (
    <>
      <div className="divide-y divide-line">
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
      {contactFor && (
        <ContactDrawer dm={contactFor} open onClose={() => setContactFor(null)} />
      )}
    </>
  );
}

function companyFacts(p: CompanyProfile): KVItem[] {
  const c = p.company;
  const hq = c.headquarters || [c.city, c.country].filter(Boolean).join(", ");
  const category = [c.industry_category, c.sub_category].filter(Boolean).map(enumLabel).join(" · ");
  const href = domainHref(c.website || c.company_domain);
  return [
    { label: "HQ", value: hq || "—" },
    { label: "Founded", value: c.founded_year || "—" },
    { label: "Category", value: category || "—" },
    { label: "Tech focus", value: c.technology_focus || "—" },
    {
      label: "Website",
      value: href ? (
        <a
          href={href}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 hover:text-accent"
        >
          {c.website || c.company_domain}
          <ExternalLink size={11} />
        </a>
      ) : (
        "—"
      ),
    },
    {
      label: "LinkedIn",
      value: c.company_linkedin ? (
        <a
          href={c.company_linkedin}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 hover:text-accent"
        >
          Company page
          <ExternalLink size={11} />
        </a>
      ) : (
        "—"
      ),
    },
    { label: "Source", value: enumLabel(c.source) },
    { label: "Confidence", value: fmtScore(c.confidence_score) },
    { label: "Canonical", value: <span className="tabular">{c.canonical_company_id}</span> },
  ];
}

export function CompanyProfilePage() {
  const { domain } = useParams<{ domain: string }>();
  const { data: p, isLoading, isError, error, refetch } = useCompanyProfile(domain);
  const [tab, setTab] = useState<TabId>("overview");

  const back = (
    <Link
      to="/companies"
      className="inline-flex items-center gap-1 text-12 text-fg-muted hover:text-fg"
    >
      <ArrowLeft size={13} />
      Companies
    </Link>
  );

  if (isLoading) {
    return (
      <>
        <div className="border-b border-line bg-base px-4 py-4">
          {back}
          <Skeleton className="mt-3 h-12 w-72" />
        </div>
        <div className="grid gap-4 p-4 lg:grid-cols-[1.6fr_1fr]">
          <div className="panel p-3.5">
            <SkeletonLines rows={7} />
          </div>
          <div className="panel p-3.5">
            <SkeletonLines rows={7} />
          </div>
        </div>
      </>
    );
  }

  if (isError || !p) {
    const notFound = error instanceof ApiError && error.status === 404;
    return (
      <>
        <div className="border-b border-line bg-base px-4 py-3">{back}</div>
        <ErrorState
          title={notFound ? `No company “${domain}”` : "Couldn't load this profile"}
          error={notFound ? undefined : error}
          onRetry={refetch}
        />
      </>
    );
  }

  const tabs: TabDef<TabId>[] = [
    { id: "overview", label: "Overview" },
    { id: "score", label: "Score" },
    { id: "opportunities", label: "Opportunities", count: p.counts.opportunities },
    { id: "people", label: "People", count: p.counts.decision_makers },
    { id: "intelligence", label: "Intelligence" },
    { id: "relationships", label: "Relationships" },
    { id: "timeline", label: "Timeline" },
    { id: "crm", label: "CRM" },
  ];

  const scorePanel = p.lead_score ? (
    <ScoreExplanation score={p.lead_score} />
  ) : (
    <EmptyState
      icon={<Gauge size={20} />}
      title="Not scored yet"
      description="This company has not been through the lead-scoring engine."
    />
  );

  return (
    <>
      <div className="bg-base">
        <div className="px-4 pt-3">{back}</div>
        <ProfileHeader profile={p} />
        <div className="px-2">
          <Tabs tabs={tabs} active={tab} onChange={setTab} />
        </div>
      </div>

      <div className="p-4">
        {tab === "overview" && (
          <div className="space-y-4">
            <SectionPanel title="Recommended Engagement Strategy" icon={<Lightbulb size={15} />}>
              <EngagementStrategy engagement={p.engagement} />
            </SectionPanel>
            <SectionPanel title="Human Review &amp; Assessment" icon={<ClipboardCheck size={15} />}>
              <LeadReviewPanel profile={p} />
            </SectionPanel>
            <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
              <div className="space-y-4">
                <SectionPanel title="Lead score" icon={<Gauge size={15} />}>
                  {scorePanel}
                </SectionPanel>
                <SectionPanel title="Signal timeline" icon={<Activity size={15} />}>
                  <SignalTimeline profile={p} />
                </SectionPanel>
              </div>
              <div className="space-y-4">
                <SectionPanel title="Company facts" icon={<Info size={15} />}>
                  <KeyValueGrid items={companyFacts(p)} />
                </SectionPanel>
                <SectionPanel title="Recognition &amp; rankings" icon={<Award size={15} />}>
                  <RecognitionCard profile={p} />
                </SectionPanel>
                <SectionPanel
                  title="Decision makers"
                  icon={<Users size={15} />}
                  actions={
                    p.counts.decision_makers > 5 ? (
                      <button
                        type="button"
                        onClick={() => setTab("people")}
                        className="text-11 text-accent hover:underline"
                      >
                        View all {p.counts.decision_makers}
                      </button>
                    ) : undefined
                  }
                >
                  {p.decision_makers.length > 0 ? (
                    <PeopleList people={p.decision_makers.slice(0, 5)} />
                  ) : (
                    <PeopleEmpty />
                  )}
                </SectionPanel>
                <SectionPanel title="Data coverage" icon={<Building2 size={15} />}>
                  <DataCoverage profile={p} />
                </SectionPanel>
              </div>
            </div>
            <CollapsibleSection
              sessionKey="company-profile-leadership"
              title="Leadership Signals"
              icon={<UserCog size={15} />}
              count={p.counts.leadership_signals}
            >
              <LeadershipSignalsSection signals={p.leadership_signals} />
            </CollapsibleSection>
          </div>
        )}

        {tab === "score" && (
          <div className="mx-auto max-w-3xl">
            <SectionPanel title="Score explanation" icon={<Gauge size={15} />}>
              {scorePanel}
            </SectionPanel>
          </div>
        )}

        {tab === "opportunities" && (
          <SectionPanel title="Opportunities" icon={<Megaphone size={15} />}>
            {p.opportunities.length > 0 ? (
              <div className="divide-y divide-line">
                {p.opportunities.map((o) => (
                  <OpportunityRow key={o.opportunity_id} opp={o} />
                ))}
              </div>
            ) : (
              <EmptyState
                icon={<Megaphone size={20} />}
                title="No opportunities"
                description="The Blog Crawler hasn't recorded market events for this company."
              />
            )}
          </SectionPanel>
        )}

        {tab === "people" && (
          <div className="space-y-4">
            <CompanyContactsSection domain={p.company.company_domain} />
            <SectionPanel title="All decision makers" icon={<Users size={15} />}>
              {p.decision_makers.length > 0 ? (
                <PeopleList people={p.decision_makers} />
              ) : (
                <PeopleEmpty />
              )}
            </SectionPanel>
          </div>
        )}

        {tab === "intelligence" && <CompanyIntelligencePanel domain={p.company.company_domain} />}

        {tab === "relationships" && (
          <CompanyRelationshipsPanel domain={p.company.company_domain} decisionMakers={p.decision_makers} />
        )}

        {tab === "timeline" && (
          <div className="mx-auto max-w-3xl">
            <SectionPanel title="Signal timeline" icon={<Activity size={15} />}>
              <SignalTimeline profile={p} />
            </SectionPanel>
          </div>
        )}

        {tab === "crm" && <CompanyCrmPanel domain={p.company.company_domain} />}
      </div>
    </>
  );
}
