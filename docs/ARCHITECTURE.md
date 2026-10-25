# Architecture

Status: target design. Sections are marked by the phase that delivers them; P1 to P8 exist today.

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
                         Argo Rollouts canary 20% → 60% → 100%                     (P7)
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
| `argocd/application.yaml` + `deploy/values.yaml` | Argo CD Application (automated sync, prune, self-heal) and the image tag it deploys, written by the `promote` job | P5 |
| `argocd/platform/prometheus-stack.yaml`, `/metrics`, ServiceMonitor, dashboard | Prometheus and Grafana installed by Argo CD; the service exposes request count and latency; a dashboard ships as a ConfigMap | P6 |
| `dora/` package + `dora.yml` | The five DORA metrics from Publish runs and PRs; JSON, markdown and a self-contained HTML dashboard; Pages deploy once the owner enables it | P8 |
| Argo Rollouts (`argocd/platform/argo-rollouts.yaml`), chart `rollout.yaml`, `analysistemplate.yaml`, `loadgen.yaml` | Canary 20% → 60% → 100% judged by Prometheus on the canary's own pods; aborts and rolls back automatically | P7 |

## Layer boundaries (service)

HTTP routes (`app/main.py`) → no business logic yet. When logic is added, put it in `app/services/` and keep routes thin.

## Deployment model

Push-based deploy is intentionally avoided. CI never holds cluster credentials; it only publishes an image and updates the desired state in Git. Argo CD reconciles the cluster to that state.
