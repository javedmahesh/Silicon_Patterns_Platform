import { useEffect, useState } from "react";
import {
  Activity,
  Building2,
  Clock,
  Globe,
  Briefcase,
  ExternalLink,
  Gauge,
  Lock,
  Mail,
  MapPin,
  Phone,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  UserRound,
} from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { toast } from "@/components/ui/Toast";
import {
  Avatar,
  Completeness,
  CopyButton,
  FieldRow,
  NotAvailable,
  SectionCard,
  SourceBadge,
  VerifiedBadge,
} from "@/components/profile/DmField";
import type { FieldSource } from "@/components/profile/DmField";
import { DmNotes } from "@/components/profile/DmNotes";
import { useDmContact, useDmDetail, usePutDmContact } from "@/lib/api/queries";
import { useAuth } from "@/lib/auth/store";
import { cleanLocation, enumLabel, fmtDate, fullName } from "@/lib/format";
import type { ContactIn, DecisionMakerOut } from "@/lib/api/types";

const val = (s?: string | null) => (s && s.trim() ? s.trim() : "");
const EMAIL_VERIFIED = new Set(["verified", "valid", "safe", "deliverable", "ok"]);
const CONF_TONE = { High: "positive", Medium: "accent", Low: "neutral" } as const;
const REL_TONE: Record<string, "positive" | "accent" | "neutral"> = {
  Strategic: "positive", Active: "positive", Engaged: "accent", Known: "neutral", Cold: "neutral",
};
const MOVEMENT_LABEL: Record<string, string> = {
  promotion: "Promotion",
  role_change: "Role Change",
  new_executive_hire: "New Hire",
  executive_departure: "Departure",
  board_appointment: "Board Appointment",
  founder_change: "Founder Change",
  executive_reshuffle: "Reshuffle",
};

function freshnessLabel(iso?: string | null): { label: string; tone: "positive" | "warning" | "neutral" } {
  if (!iso) return { label: "Unknown", tone: "neutral" };
  const days = (Date.now() - Date.parse(iso)) / 86_400_000;
  if (days <= 30) return { label: "Fresh", tone: "positive" };
  if (days <= 120) return { label: "Recent", tone: "neutral" };
  return { label: "Stale — re-enrich", tone: "warning" };
}

/**
 * Enterprise decision-maker profile panel. Surfaces every field the Apify actor
 * returns — auto-populated and provenance-labelled, with copy buttons, verification
 * badges and clickable links — laid out as CRM-style cards (Header · Contact ·
 * Company · Professional · About · Metadata · Collaboration · Timeline). Missing
 * data renders as "Not Available", never a placeholder. Heavy enrichment is loaded
 * lazily (only when the panel opens) so the directory + Company Profile stay fast.
 */
export function ContactDrawer({
  dm,
  open,
  onClose,
}: {
  dm: DecisionMakerOut;
  open: boolean;
  onClose: () => void;
}) {
  const { isManager } = useAuth(); // admin/manager may edit contact; members are read-only
  const { data: contact, isLoading } = useDmContact(dm.id, open);
  const { data: detail, isLoading: detailLoading } = useDmDetail(dm.id, open);
  const put = usePutDmContact(dm.id);
  const [form, setForm] = useState<Pick<ContactIn, "work_email" | "work_phone">>({
    work_email: "",
    work_phone: "",
  });

  // Seed the editable fields from the effective contact whenever it (re)loads.
  useEffect(() => {
    if (!open) return;
    setForm({ work_email: contact?.work_email ?? "", work_phone: contact?.work_phone ?? "" });
  }, [open, contact]);

  const set = (k: "work_email" | "work_phone") => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  function save() {
    put.mutate(
      {
        work_email: (form.work_email ?? "").trim(),
        work_phone: (form.work_phone ?? "").trim(),
        notes: contact?.notes ?? "", // preserve any legacy contact note (no longer edited here)
      },
      {
        onSuccess: () => toast("Contact details saved", "positive"),
        onError: () => toast("Couldn't save contact details", "danger"),
      },
    );
  }

  // Effective contact values + per-field provenance.
  const email = isManager ? (form.work_email ?? "").trim() : val(contact?.work_email);
  const phone = isManager ? (form.work_phone ?? "").trim() : val(contact?.work_phone);
  const emailVerified = Boolean(email) && EMAIL_VERIFIED.has((dm.email_status ?? "").toLowerCase());
  const emailSrc: FieldSource = contact?.email_overridden
    ? "overridden"
    : contact?.source_work_email
      ? "apify"
      : email
        ? "manual"
        : "none";
  const phoneSrc: FieldSource = contact?.phone_overridden
    ? "overridden"
    : contact?.source_work_phone
      ? "apify"
      : phone
        ? "manual"
        : "none";

  const name = fullName(dm.first_name, dm.last_name) || dm.full_name || "Decision maker";
  const title = dm.current_title || dm.headline || "";
  const website = val(dm.organization_website);
  const companyLinkedin = val(dm.organization_linkedin);
  const company = dm.resolved_company_name || dm.company_domain || "";
  const place = cleanLocation(
    [dm.city, dm.state_region, dm.country].filter(Boolean).join(", ") || dm.location,
  );
  const subParts = [detail?.department, detail?.business_unit, company].filter(Boolean);

  // Derived confidence from contact completeness + email verification (display only).
  const filled = [email, phone, dm.linkedin_url, website, place].filter(Boolean).length;
  const confidence =
    emailVerified && filled >= 4 ? "High" : filled >= 3 ? "Medium" : "Low";
  const fresh = freshnessLabel(detail?.ingested_at);

  // Phase 2 decision intelligence (immediate from the list row; richer from detail).
  const influenceScore = detail?.influence_score ?? dm.influence_score ?? null;
  const confidenceScore = detail?.confidence_score ?? dm.confidence_score ?? null;
  const confLevel = detail?.confidence_level || dm.confidence_level || "";
  const deptClass = detail?.department_class ?? dm.department_class ?? "";
  const deptGroup = detail?.department_group ?? dm.department_group ?? "";
  const execLevel = detail?.exec_level ?? dm.exec_level ?? "";
  const influenceFactors = detail?.influence_factors ?? [];
  const confidenceFactors = detail?.confidence_factors ?? [];
  const leadership = detail?.leadership_signals ?? [];

  return (
    <Modal
      open={open}
      onClose={onClose}
      width="46rem"
      title={
        <span className="flex items-center gap-2">
          {name}
          {dm.seniority && <Badge>{enumLabel(dm.seniority)}</Badge>}
        </span>
      }
      footer={
        isManager ? (
          <>
            <Button onClick={onClose}>Cancel</Button>
            <Button variant="primary" onClick={save} disabled={put.isPending}>
              {put.isPending ? "Saving…" : "Save"}
            </Button>
          </>
        ) : (
          <Button onClick={onClose}>Close</Button>
        )
      }
    >
      {isLoading ? (
        <div className="grid place-items-center py-10">
          <Spinner size={16} />
        </div>
      ) : (
        <div className="space-y-3">
          {/* ── Profile header ─────────────────────────────────────────────── */}
          <div className="flex items-start gap-3 rounded-lg border border-line bg-surface p-3">
            <Avatar name={name} src={dm.photo_url} size={48} />
            <div className="min-w-0 flex-1">
              <div className="truncate text-15 font-semibold text-fg">{name}</div>
              <div className="truncate text-12 text-fg-muted">{title || <NotAvailable />}</div>
              {subParts.length > 0 && (
                <div className="mt-0.5 truncate text-11 text-fg-subtle">{subParts.join(" · ")}</div>
              )}
              {place && (
                <div className="mt-0.5 flex items-center gap-1 text-11 text-fg-subtle">
                  <MapPin size={11} /> {place}
                </div>
              )}
              <div className="mt-2 flex flex-wrap gap-2">
                <Button size="sm" disabled={!email} onClick={() => email && (window.location.href = `mailto:${email}`)}>
                  <Mail size={13} /> Email
                </Button>
                <Button size="sm" disabled={!phone} onClick={() => phone && (window.location.href = `tel:${phone}`)}>
                  <Phone size={13} /> Call
                </Button>
                {dm.linkedin_url && (
                  <Button size="sm" onClick={() => window.open(dm.linkedin_url!, "_blank", "noreferrer")}>
                    <ExternalLink size={13} /> LinkedIn
                  </Button>
                )}
              </div>
            </div>
          </div>

          {/* ── Decision intelligence (influence + confidence) ─────────────── */}
          <SectionCard title="Decision Intelligence" icon={<Gauge size={12} />}>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-md border border-line bg-base p-2.5">
                <div className="text-11 text-fg-subtle">Influence score</div>
                <div className="text-22 font-semibold text-fg">
                  {influenceScore ?? "—"}
                  <span className="text-12 text-fg-subtle">/100</span>
                </div>
                <div className="mt-1 h-1.5 rounded bg-control">
                  <div className="h-1.5 rounded bg-accent" style={{ width: `${influenceScore ?? 0}%` }} />
                </div>
                {(execLevel || deptClass) && (
                  <div className="mt-1 truncate text-11 text-fg-subtle">
                    {[execLevel, deptClass].filter(Boolean).join(" · ")}
                  </div>
                )}
              </div>
              <div className="rounded-md border border-line bg-base p-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-11 text-fg-subtle">Confidence</span>
                  {confLevel && (
                    <Badge tone={CONF_TONE[confLevel as keyof typeof CONF_TONE] ?? "neutral"}>{confLevel}</Badge>
                  )}
                </div>
                <div className="text-22 font-semibold text-fg">
                  {confidenceScore ?? "—"}
                  <span className="text-12 text-fg-subtle">/100</span>
                </div>
                <div className="mt-1 h-1.5 rounded bg-control">
                  <div className="h-1.5 rounded bg-positive" style={{ width: `${confidenceScore ?? 0}%` }} />
                </div>
                {deptGroup && <div className="mt-1 truncate text-11 text-fg-subtle">{deptGroup}</div>}
              </div>
            </div>
            {(influenceFactors.length > 0 || confidenceFactors.length > 0) && (
              <div className="mt-2 flex flex-wrap gap-1">
                {influenceFactors.map((f) => (
                  <Badge key={`i-${f}`} tone="accent">{f}</Badge>
                ))}
                {confidenceFactors.map((f) => (
                  <Badge key={`c-${f}`} tone="neutral">{f}</Badge>
                ))}
              </div>
            )}
          </SectionCard>

          {/* ── Relationship (Phase 3) ─────────────────────────────────────── */}
          {detail && (detail.relationship_status || detail.next_action) && (
            <SectionCard title="Relationship" icon={<Activity size={12} />}>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-md border border-line bg-base p-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-11 text-fg-subtle">Status</span>
                    <Badge tone={REL_TONE[detail.relationship_status] ?? "neutral"}>
                      {detail.relationship_status || "Cold"}
                    </Badge>
                  </div>
                  <div className="text-18 font-semibold text-fg">
                    {detail.relationship_score ?? 0}<span className="text-12 text-fg-subtle">/100</span>
                  </div>
                </div>
                <div className="rounded-md border border-line bg-base p-2.5">
                  <div className="mb-0.5 flex items-center gap-1.5 text-11 text-fg-subtle">
                    <Clock size={11} /> Follow-up
                  </div>
                  {detail.follow_up ? (
                    <>
                      <div className="text-12 text-fg">
                        {detail.follow_up.overdue ? <span className="text-danger">Overdue</span> : "On track"}
                      </div>
                      <div className="text-11 text-fg-subtle">{detail.follow_up.reason}</div>
                    </>
                  ) : (
                    <NotAvailable />
                  )}
                </div>
              </div>
              {detail.next_action && (
                <div className="mt-2 rounded-md border border-accent/40 bg-accent/10 p-2.5">
                  <div className="mb-0.5 flex items-center gap-1.5 text-11 font-semibold text-accent">
                    <Sparkles size={12} /> Next best action · {detail.next_action.priority}
                  </div>
                  <div className="text-12 font-medium text-fg">{detail.next_action.action}</div>
                  <div className="text-11 text-fg-subtle">{detail.next_action.reason}</div>
                </div>
              )}
              {detail.risk_flags.length > 0 && (
                <div className="mt-2 flex flex-wrap items-center gap-1">
                  <span className="text-11 text-fg-subtle">Risk ({detail.risk_severity}):</span>
                  {detail.risk_flags.map((f) => (
                    <Badge key={f} tone={detail.risk_severity === "high" ? "danger" : "warning"}>{f}</Badge>
                  ))}
                </div>
              )}
            </SectionCard>
          )}

          {/* ── Card grid: Contact · Company ───────────────────────────────── */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <SectionCard title="Contact Information" icon={<Mail size={12} />}>
              {isManager ? (
                <div className="divide-y divide-line/60">
                  <div className="py-1.5">
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <span className="text-11 text-fg-subtle">Work email</span>
                      <span className="flex items-center gap-1.5">
                        {email && <VerifiedBadge verified={emailVerified} />}
                        <CopyButton value={email} />
                        <SourceBadge source={emailSrc} original={contact?.source_work_email} />
                      </span>
                    </div>
                    <Input type="email" value={form.work_email ?? ""} onChange={set("work_email")} placeholder="name@company.com" />
                  </div>
                  <div className="py-1.5">
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <span className="text-11 text-fg-subtle">Work phone</span>
                      <span className="flex items-center gap-1.5">
                        <CopyButton value={phone} />
                        <SourceBadge source={phoneSrc} original={contact?.source_work_phone} />
                      </span>
                    </div>
                    <Input type="tel" value={form.work_phone ?? ""} onChange={set("work_phone")} placeholder="+1 555 0100" />
                  </div>
                  <FieldRow label="LinkedIn" value={dm.linkedin_url ? "View profile" : ""} source={dm.linkedin_url ? "apify" : "none"} href={dm.linkedin_url} />
                  {detail?.alt_emails && <FieldRow label="Alternate emails" value={detail.alt_emails} source="apify" />}
                </div>
              ) : (
                <div className="divide-y divide-line/60">
                  <FieldRow
                    label="Work email"
                    value={email}
                    source={emailSrc}
                    original={contact?.source_work_email}
                    trailing={
                      email ? (
                        <span className="flex items-center gap-1.5">
                          <VerifiedBadge verified={emailVerified} />
                          <CopyButton value={email} />
                        </span>
                      ) : undefined
                    }
                  />
                  <FieldRow
                    label="Work phone"
                    value={phone}
                    source={phoneSrc}
                    original={contact?.source_work_phone}
                    trailing={phone ? <CopyButton value={phone} /> : undefined}
                  />
                  <FieldRow label="LinkedIn" value={dm.linkedin_url ? "View profile" : ""} source={dm.linkedin_url ? "apify" : "none"} href={dm.linkedin_url} />
                  {detail?.alt_emails && <FieldRow label="Alternate emails" value={detail.alt_emails} source="apify" />}
                </div>
              )}
            </SectionCard>

            <SectionCard title="Company Information" icon={<Building2 size={12} />}>
              <div className="divide-y divide-line/60">
                <FieldRow label="Company" value={company} source={company ? "apify" : "none"} />
                <FieldRow label="Domain" value={dm.company_domain} source={dm.company_domain ? "apify" : "none"} />
                <FieldRow
                  label="Website"
                  value={website ? website.replace(/^https?:\/\/(www\.)?/, "") : ""}
                  source={website ? "apify" : "none"}
                  href={website || undefined}
                />
                <FieldRow label="Company LinkedIn" value={companyLinkedin ? "Company page" : ""} source={companyLinkedin ? "apify" : "none"} href={companyLinkedin || undefined} />
                <FieldRow label="Industry" value={dm.industry} source={dm.industry ? "apify" : "none"} />
                <FieldRow label="Company size" value={dm.company_size} source={dm.company_size ? "apify" : "none"} />
              </div>
            </SectionCard>
          </div>

          {/* ── Professional information ───────────────────────────────────── */}
          <SectionCard title="Professional Information" icon={<Briefcase size={12} />}>
            <div className="grid grid-cols-1 gap-x-5 sm:grid-cols-2">
              <div className="divide-y divide-line/60">
                <FieldRow label="Current title" value={title} source={title ? "apify" : "none"} />
                <FieldRow label="Seniority" value={dm.seniority ? enumLabel(dm.seniority) : ""} source={dm.seniority ? "apify" : "none"} />
                <FieldRow label="Functional area" value={dm.functional_area} source={dm.functional_area ? "apify" : "none"} />
                <FieldRow label="Department" value={deptClass} source="none" />
                <FieldRow label="Function group" value={deptGroup} source="none" />
                <FieldRow label="Business unit" value={detail?.business_unit} source={detail?.business_unit ? "apify" : "none"} />
              </div>
              <div className="divide-y divide-line/60">
                <FieldRow label="Skills" value={detail?.skills} source={detail?.skills ? "apify" : "none"} />
                <FieldRow label="Languages" value={detail?.languages} source={detail?.languages ? "apify" : "none"} />
                <FieldRow label="Years in company" value={detail?.years_in_company} source={detail?.years_in_company ? "apify" : "none"} />
                <FieldRow label="Years in role" value={detail?.years_in_role} source={detail?.years_in_role ? "apify" : "none"} />
                <FieldRow label="Followers" value={detail?.followers} source={detail?.followers ? "apify" : "none"} />
                <FieldRow label="Connections" value={detail?.connections} source={detail?.connections ? "apify" : "none"} />
                <FieldRow
                  label="Engineering relevance"
                  value={detail?.engineering_relevance != null ? `${detail.engineering_relevance}/100` : ""}
                  source="none"
                />
              </div>
            </div>
            {detailLoading && !detail && (
              <div className="pt-2"><Spinner size={13} /></div>
            )}
          </SectionCard>

          {/* ── About / summary (only when present) ────────────────────────── */}
          {detail?.summary && (
            <SectionCard title="About" icon={<UserRound size={12} />}>
              <p className="whitespace-pre-wrap text-12 leading-relaxed text-fg-muted">{detail.summary}</p>
            </SectionCard>
          )}

          {/* ── Additional metadata ────────────────────────────────────────── */}
          <SectionCard title="Additional Metadata" icon={<Clock size={12} />}>
            <div className="grid grid-cols-1 gap-x-5 sm:grid-cols-2">
              <div className="divide-y divide-line/60">
                <FieldRow label="Source" value={detail?.source ? enumLabel(detail.source) : "Apify"} source="apify" />
                <FieldRow label="Last updated" value={fmtDate(detail?.ingested_at)} />
                <FieldRow label="Captured" value={fmtDate(detail?.captured_at)} />
              </div>
              <div className="divide-y divide-line/60">
                <FieldRow
                  label="Profile freshness"
                  value={fresh.label}
                  trailing={<Badge tone={fresh.tone}>{fresh.label.split(" ")[0]}</Badge>}
                />
                <FieldRow
                  label="Data confidence"
                  value={confidence}
                  trailing={<Badge tone={confidence === "High" ? "positive" : confidence === "Medium" ? "accent" : "neutral"}>{confidence}</Badge>}
                />
                <FieldRow label="Apify person id" value={detail?.apify_person_id} />
              </div>
            </div>
          </SectionCard>

          {/* ── Contact completeness ───────────────────────────────────────── */}
          <Completeness
            items={[
              { label: "Email", ok: Boolean(email) },
              { label: "Phone", ok: Boolean(phone) },
              { label: "LinkedIn", ok: Boolean(dm.linkedin_url) },
              { label: "Company Website", ok: Boolean(website) },
              { label: "Location", ok: Boolean(dm.city || dm.country || place) },
            ]}
          />

          <p className="flex items-start gap-1.5 text-11 text-fg-subtle">
            <ShieldCheck size={13} className="mt-px shrink-0" />
            Professional contact info only — no personal addresses, personal email, or personal phone numbers.
          </p>
          {!isManager && (
            <p className="flex items-start gap-1.5 text-11 text-fg-subtle">
              <Lock size={13} className="mt-px shrink-0" />
              Contact details are read-only — ask an admin or manager to update them.
            </p>
          )}

          {/* ── Internal collaboration ─────────────────────────────────────── */}
          <div className="border-t border-line pt-3">
            <div className="mb-2 flex items-center gap-1.5 text-11 font-semibold uppercase tracking-wide text-fg-subtle">
              <Sparkles size={12} /> Internal Collaboration
            </div>
            <DmNotes dmId={dm.id} open={open} />
          </div>

          {/* ── Leadership activity (integrated leadership signals) ─────────── */}
          {leadership.length > 0 && (
            <SectionCard title="Leadership Activity" icon={<TrendingUp size={12} />}>
              <ul className="space-y-1.5">
                {leadership.map((s) => (
                  <li key={s.signal_id} className="text-12">
                    <span className="flex flex-wrap items-center gap-1.5">
                      <Badge tone="accent">{MOVEMENT_LABEL[s.movement_type] ?? s.movement_type}</Badge>
                      <span className="text-fg">{s.to_title || s.person_name || s.company_name}</span>
                      {s.effective_date && <span className="text-11 text-fg-subtle">· {s.effective_date}</span>}
                    </span>
                    {s.summary && <span className="mt-0.5 block text-11 text-fg-subtle">{s.summary}</span>}
                  </li>
                ))}
              </ul>
            </SectionCard>
          )}

          {/* ── Timeline (placeholder for future work) ─────────────────────── */}
          <SectionCard title="Timeline" icon={<Clock size={12} />}>
            <div className="flex items-center gap-2 py-1 text-11 text-fg-subtle">
              <Globe size={13} />
              Engagement &amp; signal timeline for this contact is coming soon.
            </div>
          </SectionCard>
        </div>
      )}
    </Modal>
  );
}
