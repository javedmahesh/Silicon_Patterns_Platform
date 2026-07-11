"""Data access for Enterprise CRM Phase 8: AI Intelligence & Copilot (deterministic, no LLM)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from master_db.models import (
    AiBriefing,
    AiCopilotQuery,
    AiEngagementScore,
    AiInsight,
    AiRecommendation,
    AiRiskScore,
)


# ----------------------------------------------------------------- insights
def create_insight(session: Session, **kw) -> AiInsight:
    i = AiInsight(**kw)
    session.add(i)
    session.flush()
    return i


def get_insight(session: Session, insight_id: int) -> AiInsight | None:
    return session.get(AiInsight, insight_id)


def list_insights(
    session: Session, *, insight_type: str | None = None, severity: str | None = None,
    status: str | None = None, limit: int = 50, offset: int = 0,
) -> tuple[list[AiInsight], int]:
    q = select(AiInsight)
    filters = []
    if insight_type:
        filters.append(AiInsight.insight_type == insight_type)
    if severity:
        filters.append(AiInsight.severity == severity)
    if status:
        filters.append(AiInsight.status == status)
    if filters:
        q = q.where(and_(*filters))
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(q.order_by(AiInsight.id.desc()).limit(limit).offset(offset)))
    return rows, total


def count_active_insights(session: Session) -> int:
    return session.scalar(
        select(func.count()).select_from(AiInsight).where(AiInsight.status == "active")
    ) or 0


def insight_counts_by_type(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(AiInsight.insight_type, func.count(AiInsight.id))
        .where(AiInsight.status == "active")
        .group_by(AiInsight.insight_type)
    ).all()
    return {r[0]: r[1] for r in rows}


def existing_active_insight(session: Session, insight_type: str, entity_type: str, entity_id: str, title: str) -> AiInsight | None:
    """Idempotency guard so repeated generate() calls don't spam duplicate active insights."""
    return session.scalar(
        select(AiInsight).where(
            AiInsight.insight_type == insight_type, AiInsight.entity_type == entity_type,
            AiInsight.entity_id == entity_id, AiInsight.title == title, AiInsight.status == "active",
        )
    )


# ----------------------------------------------------------------- recommendations
def create_recommendation(session: Session, **kw) -> AiRecommendation:
    r = AiRecommendation(**kw)
    session.add(r)
    session.flush()
    return r


def get_recommendation(session: Session, rec_id: int) -> AiRecommendation | None:
    return session.get(AiRecommendation, rec_id)


def list_recommendations(
    session: Session, *, recommendation_type: str | None = None, status: str | None = None,
    limit: int = 50, offset: int = 0,
) -> tuple[list[AiRecommendation], int]:
    q = select(AiRecommendation)
    filters = []
    if recommendation_type:
        filters.append(AiRecommendation.recommendation_type == recommendation_type)
    if status:
        filters.append(AiRecommendation.status == status)
    if filters:
        q = q.where(and_(*filters))
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(q.order_by(AiRecommendation.id.desc()).limit(limit).offset(offset)))
    return rows, total


def count_pending_recommendations(session: Session) -> int:
    return session.scalar(
        select(func.count()).select_from(AiRecommendation).where(AiRecommendation.status == "pending")
    ) or 0


def recommendation_acceptance_stats(session: Session) -> list[tuple[str, int, int, int]]:
    """(type, total, completed, dismissed) per recommendation_type. 1 query."""
    rows = session.execute(
        select(
            AiRecommendation.recommendation_type,
            func.count(AiRecommendation.id),
            func.count(AiRecommendation.id).filter(AiRecommendation.status == "completed"),
            func.count(AiRecommendation.id).filter(AiRecommendation.status == "dismissed"),
        ).group_by(AiRecommendation.recommendation_type)
    ).all()
    return [(r[0], r[1], r[2], r[3]) for r in rows]


def existing_pending_recommendation(session: Session, recommendation_type: str, entity_type: str, entity_id: str) -> AiRecommendation | None:
    return session.scalar(
        select(AiRecommendation).where(
            AiRecommendation.recommendation_type == recommendation_type,
            AiRecommendation.entity_type == entity_type, AiRecommendation.entity_id == entity_id,
            AiRecommendation.status == "pending",
        )
    )


# ----------------------------------------------------------------- risk scores
def create_risk(session: Session, **kw) -> AiRiskScore:
    r = AiRiskScore(**kw)
    session.add(r)
    session.flush()
    return r


def list_risks(
    session: Session, *, risk_type: str | None = None, limit: int = 50, offset: int = 0,
) -> tuple[list[AiRiskScore], int]:
    q = select(AiRiskScore)
    if risk_type:
        q = q.where(AiRiskScore.risk_type == risk_type)
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(q.order_by(AiRiskScore.id.desc()).limit(limit).offset(offset)))
    return rows, total


def count_risks(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(AiRiskScore)) or 0


def risk_distribution(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(AiRiskScore.risk_type, func.count(AiRiskScore.id)).group_by(AiRiskScore.risk_type)
    ).all()
    return {r[0]: r[1] for r in rows}


def clear_risks_of_type(session: Session, risk_type: str) -> None:
    """Wipe the prior snapshot before regenerating — risk scores are a point-in-time view."""
    session.query(AiRiskScore).filter(AiRiskScore.risk_type == risk_type).delete()


# ----------------------------------------------------------------- engagement scores
def upsert_engagement_score(session: Session, entity_type: str, entity_id: str, **kw) -> AiEngagementScore:
    existing = session.scalar(
        select(AiEngagementScore).where(
            AiEngagementScore.entity_type == entity_type, AiEngagementScore.entity_id == entity_id,
        )
    )
    if existing:
        for k, v in kw.items():
            setattr(existing, k, v)
        session.flush()
        return existing
    e = AiEngagementScore(entity_type=entity_type, entity_id=entity_id, **kw)
    session.add(e)
    session.flush()
    return e


def list_engagement_scores(session: Session, *, limit: int = 50, offset: int = 0) -> tuple[list[AiEngagementScore], int]:
    q = select(AiEngagementScore)
    total = session.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = list(session.scalars(q.order_by(AiEngagementScore.score).limit(limit).offset(offset)))
    return rows, total


def avg_engagement_score(session: Session) -> float | None:
    return session.scalar(select(func.avg(AiEngagementScore.score)))


def engagement_trend_counts(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(AiEngagementScore.trend, func.count(AiEngagementScore.id)).group_by(AiEngagementScore.trend)
    ).all()
    return {r[0]: r[1] for r in rows}


# ----------------------------------------------------------------- briefings
def create_briefing(session: Session, **kw) -> AiBriefing:
    b = AiBriefing(**kw)
    session.add(b)
    session.flush()
    return b


def latest_briefing(session: Session) -> AiBriefing | None:
    return session.scalar(select(AiBriefing).order_by(AiBriefing.id.desc()).limit(1))


def list_briefings(session: Session, limit: int = 20) -> list[AiBriefing]:
    return list(session.scalars(select(AiBriefing).order_by(AiBriefing.id.desc()).limit(limit)))


def count_briefings(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(AiBriefing)) or 0


# ----------------------------------------------------------------- copilot usage
def log_copilot_query(session: Session, **kw) -> AiCopilotQuery:
    q = AiCopilotQuery(**kw)
    session.add(q)
    session.flush()
    return q


def copilot_usage_by_type(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(AiCopilotQuery.query_type, func.count(AiCopilotQuery.id)).group_by(AiCopilotQuery.query_type)
    ).all()
    return {r[0]: r[1] for r in rows}
