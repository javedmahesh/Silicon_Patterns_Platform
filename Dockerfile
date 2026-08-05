# FastAPI backend for the Silicon Patterns Platform.
# Runs the EXACT app you run locally (uvicorn backend.main:app) — no serverless adapter.
# Deploy to any container host: Railway, Render, Fly.io, Cloud Run.
#
# Pending migrations are applied automatically at startup, before the app serves its
# first request (backend/main.py -> master_db.migrate). A Postgres advisory lock
# serializes concurrent replicas, so this is safe with numReplicas > 1; a migration
# failure aborts startup rather than serving on an outdated schema. No manual step is
# needed after a deploy. Set SP_AUTO_MIGRATE=false to manage them out-of-band with
#   DATABASE_URL=... python scripts/apply_migrations.py
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY . .
RUN pip install --upgrade pip && pip install -e ".[postgres]"

# Run as an unprivileged user (the app never writes to the image filesystem — model
# artifacts, logs, and state all live in the DB / stdout).
RUN useradd --system --uid 10001 appuser && chown -R appuser /app
USER appuser

EXPOSE 8000
# Container hosts inject $PORT; default to 8000 for local `docker run`. (Platform
# health checks hit /health; this HEALTHCHECK covers a plain `docker run` too.)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/health/live').status==200 else 1)"
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
