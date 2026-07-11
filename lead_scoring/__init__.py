"""Lead Scoring service (P3).

A SEPARATE service — never embedded in any of the four engines. It consumes the
master DB (opportunities, demand_signals, decision_makers, company classification)
and produces one ``lead_scores`` row per company: a configurable weighted blend of
four 0-100 subscores, adjusted by region / prospect-type / company-tier
multipliers, graded A+/A/B/C, with a full explainable rationale.
"""
