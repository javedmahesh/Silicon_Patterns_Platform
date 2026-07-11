"""Pipeline orchestrator (P5).

Turns the platform into one runnable system. Each *stage* (industry / blog /
career / decision_maker_intelligence / scoring) ingests its component's data into the master DB
(optionally running the upstream engine first), tracked in ``pipeline_runs``.
Stages are idempotent, so any run is safe to repeat; failed stages can be
re-run or resumed from the last checkpoint. Driven by the ``sp-platform`` CLI.
"""
