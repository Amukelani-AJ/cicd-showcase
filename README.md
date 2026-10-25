# CI/CD Showcase

A small FastAPI service wrapped in a complete, free, local-first delivery pipeline: tests, container image, security gates, GitOps deployment on a local Kubernetes cluster, canary releases with automatic rollback, and DORA metrics.

The app is deliberately tiny. The pipeline is the project.

## Status

Built in stages; see [docs/PLAN.md](docs/PLAN.md) for the full roadmap.

| Stage | What | State |
|---|---|---|
| P1 | Service, tests, container, CI | Done |
| P2 | Publish to GHCR | Done |
| P3 | Security gates, SBOM, image signing | In progress |
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

## Verify a published image

Images are published to GHCR on every merge to `main`, signed keyless with cosign, and shipped with a CycloneDX SBOM attestation and build provenance.

```powershell
docker pull ghcr.io/amukelani-aj/cicd-showcase:latest

cosign verify ghcr.io/amukelani-aj/cicd-showcase:latest `
  --certificate-identity-regexp '^https://github.com/Amukelani-AJ/cicd-showcase/\.github/workflows/publish\.yml@refs/(heads/main|tags/v.*)$' `
  --certificate-oidc-issuer https://token.actions.githubusercontent.com

gh attestation verify oci://ghcr.io/amukelani-aj/cicd-showcase:latest --repo Amukelani-AJ/cicd-showcase
```

## Security gates

| Gate | Tool | Runs |
|---|---|---|
| Secrets in code and history | Gitleaks | PRs, `main`, weekly |
| Static analysis | Semgrep (pinned) | PRs, `main`, weekly |
| Dependencies, Dockerfile, workflow config | Trivy (fs) | PRs, `main`, weekly |
| Built image vulnerabilities | Trivy (image) | every PR |
| SBOM | Syft, CycloneDX | every PR and release |

All GitHub Actions are pinned to commit SHAs and updated by Dependabot. See D-007 to D-009 in [docs/DECISIONS.md](docs/DECISIONS.md) for the reasoning.

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
