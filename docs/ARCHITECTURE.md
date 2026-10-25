# Architecture

Status: target design. Sections are marked by the phase that delivers them; P1 to P4 exist today.

## Overview

```
 developer ──push/PR──▶ GitHub ──▶ GitHub Actions
                                       │  lint · test · compliance · build        (P1)
                                       │  security gates · SBOM · sign             (P3)
                                       ▼
                                     GHCR  ◀── image tagged with git SHA          (P2)
                                       │
                         CI commits new tag to manifests                           (P5)
                                       ▼
                    Argo CD ──watches Git──▶ kind cluster ◀── Helm chart           (P4, P5)
                                       │
                         Argo Rollouts canary 10% → 50% → 100%                     (P7)
                                       │ queries
                                   Prometheus ◀── /metrics from the service        (P6)
                                       │ error rate too high → rollback
```

## Components

| Component | Responsibility | Phase |
|---|---|---|
| `app/` FastAPI service | Small HTTP API that exists to be built, tested, shipped and observed | P1 |
| `Dockerfile` | Multi-stage, non-root image, version injected via build args | P1 |
| `.github/workflows/ci.yml` | Compliance, lint, tests, image build | P1 |
| `docker-compose.ci.yml` | Runs the same checks locally in Docker | P1 |
| GHCR | Image registry | P2 |
| `security.yml` | Secrets, SAST, vulnerability scanning; SBOM and signing | P3 |
| `k8s/kind-config.yaml` + `charts/cicd-showcase` | Single-node kind cluster (service on `127.0.0.1:8088`) and the hardened Helm chart | P4 |
| Argo CD | Pull-based deployment from Git | P5 |
| Prometheus + Grafana | Metrics and dashboards | P6 |
| Argo Rollouts | Canary releases with metric-driven rollback | P7 |

## Layer boundaries (service)

HTTP routes (`app/main.py`) → no business logic yet. When logic is added, put it in `app/services/` and keep routes thin.

## Deployment model

Push-based deploy is intentionally avoided. CI never holds cluster credentials; it only publishes an image and updates the desired state in Git. Argo CD reconciles the cluster to that state.
