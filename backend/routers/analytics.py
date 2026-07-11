from __future__ import annotations

from typing import Callable

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from backend import cache, services
from backend.dependencies import get_session
from backend.schemas import AnalyticsCoverage, AnalyticsSummary

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _cached(request: Request, response: Response, session: Session, key: str, build: Callable):
    """Serve an analytics payload with ETag + memo keyed on the last refresh.

    The data only changes when a refresh completes, so we tag every response with a
    version-derived ETag: a matching ``If-None-Match`` short-circuits to 304, and
    otherwise the result is memoized until the next refresh advances the version.
    """
    version = cache.refresh_version(session)
    etag = cache.etag_for(key, version)
    cache_control = f"private, max-age={request.app.state.settings.analytics_cache_seconds}"
    if cache.not_modified(request, etag):
        return Response(status_code=304, headers={"ETag": etag, "Cache-Control": cache_control})
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = cache_control
    return cache.memoize(key, version, build)


@router.get("/summary", response_model=AnalyticsSummary, summary="Platform-wide rollup")
def analytics_summary(request: Request, response: Response, session: Session = Depends(get_session)):
    return _cached(request, response, session, "analytics:summary",
                   lambda: services.analytics_summary(session))


@router.get("/coverage", response_model=AnalyticsCoverage, summary="Engine-coverage matrix")
def analytics_coverage(request: Request, response: Response, session: Session = Depends(get_session)):
    return _cached(request, response, session, "analytics:coverage",
                   lambda: services.analytics_coverage(session))
