# API design

Append-only for new routes; change existing ones deliberately and note it here.

## Conventions
- JSON everywhere. Errors use the FastAPI default `{"detail": ...}` shape until a custom format is needed.
- No auth: this is a demo service with no personal data.

## Routes

### `GET /`
Returns service identity.
```json
{"service": "cicd-showcase", "message": "Hello from the pipeline"}
```

### `GET /health`
Liveness/readiness probe. Always `200` while the process is serving.
```json
{"status": "ok"}
```

### `GET /version`
Build metadata, injected at image build time via `APP_VERSION` and `GIT_SHA` (defaults: `dev`, `unknown`).
```json
{"version": "0.1.0", "git_sha": "abc1234"}
```

### `GET /metrics`
Prometheus text exposition (not in the OpenAPI schema). Scraped by Prometheus every 15–30s; requests to `/metrics` are not counted.

| Metric | Type | Labels |
|---|---|---|
| `http_requests_total` | counter | `method`, `path` (route template, or `unmatched`), `status` |
| `http_request_duration_seconds` | histogram | `method`, `path` |

Labelling by route template keeps cardinality bounded: every unknown URL lands in `path="unmatched"`.

## Failure injection (demo only)

`FAIL_RATE` (env var, float 0 to 1, default 0) makes `GET /` return `500 {"detail": "injected failure"}` for that fraction of requests. Values outside the range are clamped; unparsable values mean 0. `/health`, `/version` and `/metrics` are never affected, so probes stay green while the error rate climbs. P7 uses this to ship a deliberately bad release and prove the canary rolls back.
