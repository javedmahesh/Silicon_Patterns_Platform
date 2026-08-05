"""Enterprise CRM Phase 8: AI Intelligence & Copilot.

Deterministic, rules-based "AI" — every insight/recommendation/risk/summary is computed
directly from existing CRM data via existing repos/services (deal_repo, cs_repo,
revops_service, workflow_service, outreach_repo, campaign_repo). No external LLM calls,
no network I/O, fully reproducible given the same data.
"""
from __future__ import annotations

import time

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import admin_service
from backend import ai_repo as repo
from backend import campaign_repo
from backend import cs_repo
from backend import deal_repo
from backend import outreach_repo
from backend import revops_repo
from backend import revops_service
from backend import workflow_repo
from backend import workflow_service
from backend.schemas import (
    AiAnalyticsOut,
    AiBriefingOut,
    AiCopilotSummaryOut,
    AiDashboardOut,
    AiEngagementScoreOut,
    AiGenerationResultOut,
    AiInsightOut,
    AiRecommendationAcceptanceOut,
    AiRecommendationOut,
    AiRiskScoreOut,
    Page,
)
from master_db.models import Campaign, CrmDeal, Opportunity, User

from backend.timeutil import utc as _utc, utcnow as _utcnow


def _is_manager(user) -> bool:
    return getattr(user, "role", "member") in ("admin", "manager")


def _load_user_emails(session: Session, ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    rows = session.scalars(select(User).where(User.id.in_(ids))).all()
    return {u.id: u.email for u in rows}


_STALE_DEAL_DAYS = 14
_RENEWAL_WINDOW_DAYS = 60


def _deal_age_days(deal: CrmDeal) -> float:
    la = _utc(deal.last_activity_at) or _utc(deal.created_at) or _utcnow()
    return (_utcnow() - la).total_seconds() / 86400


# ================================================================== insight generation
def generate_insights(session: Session, user) -> AiGenerationResultOut:
    generated = 0

    def _add(insight_type, entity_type, entity_id, title, detail, severity, confidence):
        nonlocal generated
        if repo.existing_active_insight(session, insight_type, entity_type, str(entity_id), title):
            return
        repo.create_insight(
            session, insight_type=insight_type, entity_type=entity_type, entity_id=str(entity_id),
            title=title, detail=detail, severity=severity, confidence=confidence,
        )
        generated += 1

    # --- deal insights: stalled deals + unusually large deals
    open_deals = revops_repo.open_deals(session)
    stalled = [d for d in open_deals if _deal_age_days(d) > _STALE_DEAL_DAYS]
    for d in stalled:
        age = int(_deal_age_days(d))
        _add("deal", "deal", d.id, f"Deal '{d.title}' has been stalled for {age} days",
             f"No activity recorded since {age} days ago. Consider following up or re-qualifying.",
             "high" if age > 30 else "medium", "high")

    if open_deals:
        avg_value = sum(d.value or 0 for d in open_deals) / len(open_deals)
        for d in open_deals:
            if avg_value and (d.value or 0) >= avg_value * 2:
                _add("deal", "deal", d.id, f"Deal '{d.title}' is a large deal",
                     f"Value ${d.value:,.0f} is {round((d.value or 0) / avg_value, 1)}x the average open-deal value.",
                     "low", "medium")

    # --- customer insights: at-risk accounts + ARR concentration
    accounts, _ = cs_repo.list_accounts(session, limit=500)
    for a in accounts:
        health = cs_repo.latest_health(session, a.id)
        if a.status == "at_risk" or (health and health.grade in ("D", "F")):
            _add("customer", "customer", a.id, f"Account '{a.name}' is at risk",
                 f"status={a.status}, health_grade={health.grade if health else 'n/a'}.",
                 "high", "high" if health else "medium")

    total_arr = sum(a.arr or 0 for a in accounts)
    if total_arr:
        for a in accounts:
            share = (a.arr or 0) / total_arr
            if share >= 0.3:
                _add("customer", "customer", a.id, f"Account '{a.name}' is a concentration risk",
                     f"This account is {round(share * 100, 1)}% of total ARR — losing it would be material.",
                     "medium", "high")

    # --- opportunity insights: high-score opportunities not yet turned into a deal
    linked_opp_ids = {row[0] for row in session.execute(
        select(CrmDeal.opportunity_id).where(CrmDeal.opportunity_id.isnot(None))
    ).all()}
    high_score_opps = session.scalars(
        select(Opportunity).where(Opportunity.effective_opportunity_score >= 70).limit(100)
    ).all()
    for o in high_score_opps:
        if o.opportunity_id not in linked_opp_ids:
            _add("opportunity", "opportunity", o.opportunity_id,
                 f"High-score opportunity for {o.company_name or o.company_domain} has no deal",
                 f"effective_opportunity_score={o.effective_opportunity_score}, no linked CRM deal yet.",
                 "medium", "medium")

    # --- campaign insights: low-conversion active campaigns
    campaigns = session.scalars(select(Campaign).where(Campaign.status == "active")).all()
    if campaigns:
        stats = campaign_repo.campaign_stats_batch(session, [c.id for c in campaigns])
        for c in campaigns:
            s = stats.get(c.id, {})
            members = s.get("member_count", 0)
            if members >= 10:
                rate = s.get("converted_count", 0) / members
                if rate < 0.05:
                    _add("campaign", "campaign", c.id, f"Campaign '{c.name}' has low conversion",
                         f"{s.get('converted_count', 0)}/{members} members converted ({round(rate * 100, 1)}%).",
                         "low", "medium")

    # --- pipeline insights: low win rate
    pipelines = deal_repo.list_pipelines(session, active_only=True, limit=100, offset=0)[0]
    for p in pipelines:
        counts = revops_repo.company_wide_deal_counts(session, pipeline_id=p.id)
        closed = counts["won"] + counts["lost"]
        if closed >= 5:
            win_rate = counts["won"] / closed
            if win_rate < 0.2:
                _add("pipeline", "pipeline", p.id, f"Pipeline '{p.name}' has a low win rate",
                     f"win_rate={round(win_rate * 100, 1)}% over {closed} closed deals.",
                     "medium", "high")

    # --- revenue insights: forecast accuracy variance
    accuracy_rows = revops_service.forecast_accuracy(session, user)
    for a in accuracy_rows:
        if a.accuracy_pct < 70:
            _add("revenue", "forecast_snapshot", a.snapshot_id,
                 f"Forecast variance for {a.period_key} ({a.category})",
                 f"forecasted=${a.forecasted_amount:,.0f}, actual=${a.actual_amount:,.0f}, accuracy={a.accuracy_pct}%.",
                 "high", "high")

    admin_service.log_audit_event(session, category="ai_action", action="insights_generated", actor=user, detail={"generated": generated})
    session.commit()
    return AiGenerationResultOut(generated=generated)


def _insight_out(i) -> AiInsightOut:
    return AiInsightOut(
        id=i.id, insight_type=i.insight_type, entity_type=i.entity_type, entity_id=i.entity_id,
        title=i.title, detail=i.detail, severity=i.severity, confidence=i.confidence, status=i.status,
        generated_at=_utc(i.generated_at), created_at=_utc(i.created_at),
    )


def list_insights(session: Session, user, *, insight_type=None, severity=None, status=None, limit=50, offset=0) -> Page:
    rows, total = repo.list_insights(session, insight_type=insight_type, severity=severity, status=status, limit=limit, offset=offset)
    return Page.build([_insight_out(i) for i in rows], total, max(1, offset // limit + 1) if limit else 1, limit)


def patch_insight_status(session: Session, insight_id: int, new_status: str, user) -> AiInsightOut:
    i = repo.get_insight(session, insight_id)
    if not i:
        raise HTTPException(404, "insight not found")
    if new_status not in ("active", "dismissed", "resolved"):
        raise HTTPException(422, "invalid status")
    i.status = new_status
    session.commit()
    return _insight_out(i)


# ================================================================== recommendation generation
def generate_recommendations(session: Session, user) -> AiGenerationResultOut:
    generated = 0

    def _add(rec_type, entity_type, entity_id, title, detail, priority="medium"):
        nonlocal generated
        if repo.existing_pending_recommendation(session, rec_type, entity_type, str(entity_id)):
            return
        repo.create_recommendation(
            session, recommendation_type=rec_type, entity_type=entity_type, entity_id=str(entity_id),
            title=title, detail=detail, priority=priority,
        )
        generated += 1

    open_deals = revops_repo.open_deals(session)
    for d in open_deals:
        age = _deal_age_days(d)
        if age > 5:
            _add("next_best_action", "deal", d.id, f"Follow up on '{d.title}'",
                 f"No activity in {int(age)} days — send a follow-up message or schedule a call.",
                 "high" if age > _STALE_DEAL_DAYS else "medium")
        if age > _STALE_DEAL_DAYS:
            _add("deal_acceleration", "deal", d.id, f"Accelerate '{d.title}'",
                 "This deal is stalled — escalate internally or offer a concession to move it forward.",
                 "high")

    accounts, _ = cs_repo.list_accounts(session, limit=500)
    for a in accounts:
        if a.status == "at_risk":
            _add("customer_retention", "customer", a.id, f"Retention outreach for '{a.name}'",
                 "Account is flagged at-risk — schedule an executive check-in before renewal.",
                 "high")
        health = cs_repo.latest_health(session, a.id)
        if health and health.grade in ("A", "B") and a.lifecycle_stage == "growth":
            _add("expansion_opportunity", "customer", a.id, f"Expansion opportunity: '{a.name}'",
                 f"Healthy account (grade {health.grade}) in growth stage — propose an upsell.",
                 "medium")
        events = cs_repo.lifecycle_history(session, a.id)
        last_event_at = max((e.created_at for e in events), default=a.created_at)
        if (_utcnow() - (_utc(last_event_at) or _utcnow())).days > 30:
            _add("follow_up", "customer", a.id, f"Check in with '{a.name}'",
                 "No lifecycle activity recorded in 30+ days — schedule a check-in.",
                 "low")

    contracts = cs_repo.renewals_due(session, days=_RENEWAL_WINDOW_DAYS)
    for c in contracts:
        _add("renewal_action", "customer", c.account_id, f"Start renewal conversation (contract '{c.name}')",
             f"Contract ends {_utc(c.end_date)} — begin the renewal conversation now.",
             "high")

    admin_service.log_audit_event(session, category="ai_action", action="recommendations_generated", actor=user, detail={"generated": generated})
    session.commit()
    return AiGenerationResultOut(generated=generated)


def _rec_out(r) -> AiRecommendationOut:
    return AiRecommendationOut(
        id=r.id, recommendation_type=r.recommendation_type, entity_type=r.entity_type, entity_id=r.entity_id,
        title=r.title, detail=r.detail, priority=r.priority, status=r.status,
        generated_at=_utc(r.generated_at), dismissed_at=_utc(r.dismissed_at),
        completed_at=_utc(r.completed_at), completed_by=r.completed_by,
    )


def list_recommendations(session: Session, user, *, recommendation_type=None, status=None, limit=50, offset=0) -> Page:
    rows, total = repo.list_recommendations(session, recommendation_type=recommendation_type, status=status, limit=limit, offset=offset)
    return Page.build([_rec_out(r) for r in rows], total, max(1, offset // limit + 1) if limit else 1, limit)


def dismiss_recommendation(session: Session, rec_id: int, user) -> AiRecommendationOut:
    r = repo.get_recommendation(session, rec_id)
    if not r:
        raise HTTPException(404, "recommendation not found")
    r.status = "dismissed"
    r.dismissed_at = _utcnow()
    session.commit()
    return _rec_out(r)


def complete_recommendation(session: Session, rec_id: int, user) -> AiRecommendationOut:
    r = repo.get_recommendation(session, rec_id)
    if not r:
        raise HTTPException(404, "recommendation not found")
    r.status = "completed"
    r.completed_at = _utcnow()
    r.completed_by = user.id
    session.commit()
    return _rec_out(r)


# ================================================================== risk detection
def detect_risks(session: Session, user) -> AiGenerationResultOut:
    generated = 0
    for risk_type in ("stalled_deal", "at_risk_customer", "low_engagement", "missed_sla", "forecast_variance", "renewal_risk"):
        repo.clear_risks_of_type(session, risk_type)

    open_deals = revops_repo.open_deals(session)
    for d in open_deals:
        age = _deal_age_days(d)
        if age > _STALE_DEAL_DAYS:
            score = min(100.0, age * 3)
            repo.create_risk(session, risk_type="stalled_deal", entity_type="deal", entity_id=str(d.id),
                              score=score, severity="high" if score >= 60 else "medium",
                              detail={"days_stalled": int(age), "value": d.value})
            generated += 1

    accounts, _ = cs_repo.list_accounts(session, limit=500)
    for a in accounts:
        health = cs_repo.latest_health(session, a.id)
        grade = health.grade if health else None
        if a.status == "at_risk" or grade in ("D", "F"):
            score = 100.0 if grade == "F" else 80.0 if grade == "D" else 60.0
            repo.create_risk(session, risk_type="at_risk_customer", entity_type="customer", entity_id=str(a.id),
                              score=score, severity="critical" if score >= 90 else "high",
                              detail={"status": a.status, "grade": grade})
            generated += 1

    engagement_rows, _ = repo.list_engagement_scores(session, limit=1000)
    for e in engagement_rows:
        if e.score < 40:
            repo.create_risk(session, risk_type="low_engagement", entity_type=e.entity_type, entity_id=e.entity_id,
                              score=100.0 - e.score, severity="high" if e.score < 20 else "medium",
                              detail={"engagement_score": e.score, "trend": e.trend})
            generated += 1

    for tracker_status in ("breached", "escalated"):
        trackers, _ = workflow_repo.list_trackers(session, status=tracker_status, limit=200)
        for t in trackers:
            repo.create_risk(session, risk_type="missed_sla", entity_type=t.entity_type, entity_id=t.entity_id,
                              score=90.0 if tracker_status == "escalated" else 70.0,
                              severity="critical" if tracker_status == "escalated" else "high",
                              detail={"tracker_id": t.id, "status": tracker_status})
            generated += 1

    for a in revops_service.forecast_accuracy(session, user):
        if a.accuracy_pct < 70:
            repo.create_risk(session, risk_type="forecast_variance", entity_type="forecast_snapshot",
                              entity_id=str(a.snapshot_id), score=100.0 - a.accuracy_pct,
                              severity="high" if a.accuracy_pct < 50 else "medium",
                              detail={"period_key": a.period_key, "variance": a.variance})
            generated += 1

    for c in cs_repo.renewals_due(session, days=30):
        acct = cs_repo.get_account(session, c.account_id)
        health = cs_repo.latest_health(session, c.account_id) if acct else None
        if health and health.grade in ("C", "D", "F"):
            score = {"C": 50.0, "D": 75.0, "F": 95.0}[health.grade]
            repo.create_risk(session, risk_type="renewal_risk", entity_type="customer", entity_id=str(c.account_id),
                              score=score, severity="high" if score >= 75 else "medium",
                              detail={"contract": c.name, "grade": health.grade, "end_date": str(_utc(c.end_date))})
            generated += 1

    admin_service.log_audit_event(session, category="ai_action", action="risks_detected", actor=user, detail={"generated": generated})
    session.commit()
    return AiGenerationResultOut(generated=generated)


def _risk_out(r) -> AiRiskScoreOut:
    return AiRiskScoreOut(
        id=r.id, risk_type=r.risk_type, entity_type=r.entity_type, entity_id=r.entity_id,
        score=r.score, severity=r.severity, detail=r.detail or {}, generated_at=_utc(r.generated_at),
    )


def list_risks(session: Session, user, *, risk_type=None, limit=50, offset=0) -> Page:
    rows, total = repo.list_risks(session, risk_type=risk_type, limit=limit, offset=offset)
    return Page.build([_risk_out(r) for r in rows], total, max(1, offset // limit + 1) if limit else 1, limit)


# ================================================================== engagement scoring
def compute_engagement_scores(session: Session, user) -> AiGenerationResultOut:
    accounts, _ = cs_repo.list_accounts(session, limit=500)
    existing_rows, _ = repo.list_engagement_scores(session, limit=1000)
    prior_by_key = {(r.entity_type, r.entity_id): r for r in existing_rows}
    generated = 0
    for a in accounts:
        domain = a.company_domain
        if not domain:
            continue
        _, task_total = outreach_repo.list_tasks(session, company_domain=domain, limit=1)
        _, done_total = outreach_repo.list_tasks(session, company_domain=domain, status="completed", limit=1)
        _, meeting_total = outreach_repo.list_meetings(session, company_domain=domain, limit=1)

        task_score = round((done_total / task_total) * 100, 1) if task_total else 0.0
        meeting_score = min(100.0, meeting_total * 20.0)
        # ponytail: email activity proxied via task volume — no direct message<->company_domain
        # join exists yet. Upgrade path: join OutreachMessage through OutreachLead.company_domain
        # if a real per-channel breakdown is needed.
        email_score = min(100.0, task_total * 5.0)
        overall = round((email_score + meeting_score + task_score) / 3, 1)

        prior_row = prior_by_key.get(("customer", str(a.id)))
        if prior_row is None:
            trend = "stable"
        elif overall > prior_row.score + 5:
            trend = "up"
        elif overall < prior_row.score - 5:
            trend = "down"
        else:
            trend = "stable"

        repo.upsert_engagement_score(
            session, entity_type="customer", entity_id=str(a.id),
            score=overall, email_activity_score=email_score, meeting_activity_score=meeting_score,
            task_completion_score=task_score, trend=trend, computed_at=_utcnow(),
        )
        generated += 1
    session.commit()
    return AiGenerationResultOut(generated=generated)


def _engagement_out(e) -> AiEngagementScoreOut:
    return AiEngagementScoreOut(
        id=e.id, entity_type=e.entity_type, entity_id=e.entity_id, score=e.score,
        email_activity_score=e.email_activity_score, meeting_activity_score=e.meeting_activity_score,
        task_completion_score=e.task_completion_score, trend=e.trend, computed_at=_utc(e.computed_at),
    )


def list_engagement_scores(session: Session, user, *, limit=50, offset=0) -> Page:
    rows, total = repo.list_engagement_scores(session, limit=limit, offset=offset)
    return Page.build([_engagement_out(e) for e in rows], total, max(1, offset // limit + 1) if limit else 1, limit)


# ================================================================== AI Copilot
def _log_copilot(session: Session, query_type: str, entity_type: str, entity_id: str, user, summary: str) -> None:
    repo.log_copilot_query(
        session, query_type=query_type, entity_type=entity_type, entity_id=entity_id,
        user_id=getattr(user, "id", None), response_summary=summary[:2000],
    )
    session.commit()


def customer_summary(session: Session, account_id: int, user) -> AiCopilotSummaryOut:
    a = cs_repo.get_account(session, account_id)
    if not a:
        raise HTTPException(404, "account not found")
    health = cs_repo.latest_health(session, account_id)
    risks = cs_repo.list_risks(session, account_id, status="open")
    summary = (
        f"{a.name} is a {a.tier} account with ${a.arr:,.0f} ARR and ${a.mrr:,.0f} MRR "
        f"({a.status}, lifecycle: {a.lifecycle_stage}). "
        f"Health: {health.grade if health else 'not yet scored'} "
        f"({health.trend if health else 'n/a'} trend). "
        f"{len(risks)} open risk(s). "
        f"Renewal date: {a.renewal_date or 'not set'}."
    )
    _log_copilot(session, "customer_summary", "customer", str(account_id), user, summary)
    return AiCopilotSummaryOut(query_type="customer_summary", entity_type="customer", entity_id=str(account_id), summary=summary, generated_at=_utcnow())


def deal_summary(session: Session, deal_id: int, user) -> AiCopilotSummaryOut:
    d = deal_repo.get_deal(session, deal_id)
    if not d:
        raise HTTPException(404, "deal not found")
    stage = deal_repo.get_stage(session, d.stage_id)
    age = int(_deal_age_days(d))
    summary = (
        f"'{d.title}' ({d.company_domain}) is worth ${d.value or 0:,.0f} at {d.probability}% probability, "
        f"currently in stage '{stage.name if stage else 'unknown'}'. "
        f"Last activity {age} day(s) ago. Forecast category: {d.forecast_category}."
    )
    _log_copilot(session, "deal_summary", "deal", str(deal_id), user, summary)
    return AiCopilotSummaryOut(query_type="deal_summary", entity_type="deal", entity_id=str(deal_id), summary=summary, generated_at=_utcnow())


def pipeline_summary(session: Session, pipeline_id: int, user) -> AiCopilotSummaryOut:
    analytics = revops_service.pipeline_analytics(session, user, pipeline_id=pipeline_id)
    summary = (
        f"Pipeline #{pipeline_id}: {analytics.total_deals} total deals ({analytics.open_deals} open, "
        f"{analytics.won_deals} won, {analytics.lost_deals} lost). Win rate {round(analytics.win_rate * 100, 1)}%. "
        f"Pipeline value ${analytics.pipeline_value:,.0f}, weighted ${analytics.weighted_pipeline:,.0f}. "
        f"Health score {analytics.pipeline_health_score}."
    )
    _log_copilot(session, "pipeline_summary", "pipeline", str(pipeline_id), user, summary)
    return AiCopilotSummaryOut(query_type="pipeline_summary", entity_type="pipeline", entity_id=str(pipeline_id), summary=summary, generated_at=_utcnow())


def executive_summary(session: Session, user) -> AiCopilotSummaryOut:
    dash = revops_service.executive_dashboard(session, user)
    summary = (
        f"Trailing-12-month revenue ${dash.revenue_ttm:,.0f}. Pipeline value ${dash.pipeline_value:,.0f} "
        f"(weighted ${dash.weighted_forecast:,.0f}), win rate {round(dash.win_rate * 100, 1)}%. "
        f"ARR ${dash.arr:,.0f}, MRR ${dash.mrr:,.0f}, {dash.active_customers} active customers, "
        f"churn rate {round(dash.churn_rate * 100, 1)}%, {dash.expansion_accounts} accounts in expansion."
    )
    _log_copilot(session, "executive_summary", "", "", user, summary)
    return AiCopilotSummaryOut(query_type="executive_summary", entity_type="", entity_id="", summary=summary, generated_at=_utcnow())


def activity_summary(session: Session, entity_type: str, entity_id: str, user) -> AiCopilotSummaryOut:
    if entity_type != "customer":
        raise HTTPException(422, "activity_summary currently supports entity_type='customer'")
    a = cs_repo.get_account(session, int(entity_id))
    if not a or not a.company_domain:
        raise HTTPException(404, "account not found or has no linked company")
    _, task_total = outreach_repo.list_tasks(session, company_domain=a.company_domain, limit=1)
    _, done_total = outreach_repo.list_tasks(session, company_domain=a.company_domain, status="completed", limit=1)
    _, meeting_total = outreach_repo.list_meetings(session, company_domain=a.company_domain, limit=1)
    summary = (
        f"Activity for {a.name}: {task_total} task(s) ({done_total} completed), "
        f"{meeting_total} meeting(s) on record."
    )
    _log_copilot(session, "activity_summary", entity_type, entity_id, user, summary)
    return AiCopilotSummaryOut(query_type="activity_summary", entity_type=entity_type, entity_id=entity_id, summary=summary, generated_at=_utcnow())


def entity_summary(session: Session, entity_type: str, entity_id: str, user) -> AiCopilotSummaryOut:
    if entity_type == "customer":
        return customer_summary(session, int(entity_id), user)
    if entity_type == "deal":
        return deal_summary(session, int(entity_id), user)
    if entity_type == "pipeline":
        return pipeline_summary(session, int(entity_id), user)
    raise HTTPException(422, f"unsupported entity_type for summary: {entity_type}")


# ================================================================== executive briefings
def generate_briefing(session: Session, user) -> AiBriefingOut:
    dash = revops_service.executive_dashboard(session, user)
    wf_dash = workflow_service.workflow_dashboard(session, user)
    at_risk_accounts, _ = cs_repo.list_accounts(session, status="at_risk", limit=10)
    contracts = cs_repo.renewals_due(session, days=_RENEWAL_WINDOW_DAYS)

    accounts, _ = cs_repo.list_accounts(session, limit=500)
    expansion_candidates = []
    for a in accounts:
        health = cs_repo.latest_health(session, a.id)
        if health and health.grade in ("A", "B") and a.lifecycle_stage == "growth":
            expansion_candidates.append({"account_id": a.id, "name": a.name, "grade": health.grade})
    expansion_candidates = expansion_candidates[:10]

    sections = {
        "revenue_highlights": {
            "revenue_ttm": dash.revenue_ttm, "arr": dash.arr, "mrr": dash.mrr,
            "pipeline_value": dash.pipeline_value, "win_rate": dash.win_rate,
        },
        "pipeline_changes": {
            "weighted_forecast": dash.weighted_forecast, "sales_velocity": dash.sales_velocity,
        },
        "customer_risks": [{"account_id": a.id, "name": a.name, "arr": a.arr} for a in at_risk_accounts],
        "expansion_opportunities": expansion_candidates,
        "renewal_outlook": {
            "contracts_due": len(contracts),
            "total_value": sum(c.value or 0 for c in contracts),
        },
        "workflow_alerts": {
            "sla_breaches": wf_dash.sla_breaches, "pending_approvals": wf_dash.pending_approvals,
            "failure_count": wf_dash.failure_count,
        },
    }
    b = repo.create_briefing(session, period=_utcnow().strftime("%Y-%m"), sections=sections, generated_by=user.id)
    session.commit()
    return _briefing_out(b)


def _briefing_out(b) -> AiBriefingOut:
    return AiBriefingOut(id=b.id, period=b.period, sections=b.sections or {}, generated_by=b.generated_by, generated_at=_utc(b.generated_at))


def list_briefings(session: Session, user, limit: int = 20) -> list[AiBriefingOut]:
    return [_briefing_out(b) for b in repo.list_briefings(session, limit=limit)]


def latest_briefing(session: Session, user) -> AiBriefingOut | None:
    b = repo.latest_briefing(session)
    return _briefing_out(b) if b else None


# ================================================================== dashboard + analytics (cached)
_DASH_TTL_SECONDS = 30
_dash_cache: dict[str, tuple[float, AiDashboardOut]] = {}


def _cache_key(session: Session) -> str:
    try:
        return str(session.get_bind().url)
    except Exception:
        return "default"


def ai_dashboard(session: Session, user) -> AiDashboardOut:
    key = _cache_key(session)
    cached = _dash_cache.get(key)
    if cached and time.monotonic() - cached[0] < _DASH_TTL_SECONDS:
        return cached[1]

    recent, _ = repo.list_insights(session, limit=5)
    b = repo.latest_briefing(session)
    out = AiDashboardOut(
        active_insights=repo.count_active_insights(session),
        pending_recommendations=repo.count_pending_recommendations(session),
        active_risks=repo.count_risks(session),
        latest_briefing=_briefing_out(b) if b else None,
        avg_engagement_score=repo.avg_engagement_score(session),
        recent_ai_activity=[_insight_out(i) for i in recent],
    )
    _dash_cache[key] = (time.monotonic(), out)
    return out


def ai_analytics(session: Session, user) -> AiAnalyticsOut:
    acceptance = [
        AiRecommendationAcceptanceOut(
            recommendation_type=t, total=total, completed=completed, dismissed=dismissed,
            acceptance_rate=round(completed / total, 4) if total else 0.0,
        )
        for t, total, completed, dismissed in repo.recommendation_acceptance_stats(session)
    ]
    return AiAnalyticsOut(
        insight_counts=repo.insight_counts_by_type(session),
        recommendation_acceptance=acceptance,
        risk_distribution=repo.risk_distribution(session),
        avg_engagement_score=repo.avg_engagement_score(session),
        engagement_trend_counts=repo.engagement_trend_counts(session),
        copilot_usage_by_type=repo.copilot_usage_by_type(session),
        executive_briefings_generated=repo.count_briefings(session),
    )
