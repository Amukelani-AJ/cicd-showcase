# CI/CD Showcase

A small FastAPI service wrapped in a complete, free, local-first delivery pipeline: tests, container image, security gates, GitOps deployment on a local Kubernetes cluster, canary releases with automatic rollback, and DORA metrics.

The app is deliberately tiny. The pipeline is the project.

## Status

Built in stages; see [docs/PLAN.md](docs/PLAN.md) for the full roadmap.

| Stage | What | State |
|---|---|---|
| P1 | Service, tests, container, CI | Built, verified locally |
| P2 | Publish to GHCR | Planned |
| P3 | Security gates, SBOM, image signing | Planned |
| P4–P5 | kind, Helm, Argo CD GitOps | Planned |
| P6–P7 | Prometheus, canary with auto rollback | Planned |
| P8 | DORA metrics dashboard | Planned |

## Run it

```powershell
docker build -t cicd-showcase:dev --build-arg APP_VERSION=0.1.0 --build-arg GIT_SHA=local .
docker run --rm -p 8000:8000 cicd-showcase:dev
# http://localhost:8000/docs for the OpenAPI UI
```

## Run the CI locally

The same checks GitHub runs (lint, format, tests with an 80% coverage gate), in Docker:

```powershell
docker compose -f docker-compose.ci.yml --profile python run --rm ci-python
```

## API

| Route | Purpose |
|---|---|
| `GET /` | Service identity |
| `GET /health` | Liveness/readiness |
| `GET /version` | Build version and git SHA, injected at image build time |

Details in [docs/API_DESIGN.md](docs/API_DESIGN.md).

## Design

- [Architecture](docs/ARCHITECTURE.md): target topology and the phase that delivers each part
- [Decision log](docs/DECISIONS.md): why FastAPI, GHCR, kind, pip pins, squash merges

## Project conventions

Work happens on branches and lands through pull requests. Every change is recorded in [WORKLOG.md](WORKLOG.md), code files carry cumulative attribution headers, and `scripts/validate-compliance.py` enforces the hygiene rules in CI. See [CLAUDE.md](CLAUDE.md).
