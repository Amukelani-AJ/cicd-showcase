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
