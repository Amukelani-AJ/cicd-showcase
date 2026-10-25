# Written by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Initial FastAPI service: root, health and version routes
# Modified by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Added Prometheus metrics middleware, /metrics, and FAIL_RATE failure injection for the canary demo
import os
import random
import time

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

SERVICE_NAME = "cicd-showcase"

app = FastAPI(title=SERVICE_NAME)

REQUESTS = Counter("http_requests_total", "HTTP requests handled", ["method", "path", "status"])
LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency in seconds", ["method", "path"]
)


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    start = time.perf_counter()
    status = 500  # stays 500 if the handler raises before producing a response
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        # Label by route template, not the raw URL, so label cardinality stays bounded.
        route = request.scope.get("route")
        path = route.path if route else "unmatched"
        if path != "/metrics":
            REQUESTS.labels(request.method, path, str(status)).inc()
            LATENCY.labels(request.method, path).observe(time.perf_counter() - start)


def _fail_rate() -> float:
    """Fraction of requests to `/` that fail on purpose (0..1). Read per request so tests can change it."""
    try:
        return min(max(float(os.environ.get("FAIL_RATE", "0")), 0.0), 1.0)
    except ValueError:
        return 0.0


@app.get("/")
def root() -> dict[str, str]:
    if random.random() < _fail_rate():
        raise HTTPException(status_code=500, detail="injected failure")
    return {"service": SERVICE_NAME, "message": "Hello from the pipeline"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/version")
def version() -> dict[str, str]:
    return {
        "version": os.environ.get("APP_VERSION", "dev"),
        "git_sha": os.environ.get("GIT_SHA", "unknown"),
    }


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
