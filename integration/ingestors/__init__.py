"""Ingestors — read each engine's output and upsert it into the master DB.

One ingestor per engine output, all built on :class:`~integration.ingestors.base.BaseIngestor`:

  * :class:`~integration.ingestors.industry.IndustryIngestor`        -> companies
  * :class:`~integration.ingestors.blog.BlogIngestor`                -> opportunities
  * :class:`~integration.ingestors.career.JobsIngestor`              -> jobs
  * :class:`~integration.ingestors.career.DemandSignalsIngestor`     -> demand_signals
  * :class:`~integration.ingestors.career.CompanyRollupsIngestor`    -> company_rollups
  * :class:`~integration.ingestors.linkedin.LinkedInIngestor`        -> decision_makers

Every ingestor is idempotent (re-running upserts in place) and routes company
identity through :class:`~integration.resolver.CompanyResolver`, so duplicate
companies/opportunities/contacts cannot be created. Ingestors never modify the
four engines and never write to a table they do not own.
"""
