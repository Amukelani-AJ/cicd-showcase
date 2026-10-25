# Plan

Goal: one coherent delivery pipeline, built in stages, each stage a milestone in the history. Phases are sequential; one at a time.

Status key: ⬜ Not started · 🚀 In Progress · ✅ Done

| Phase | Name | Status |
|---|---|---|
| P0 | Governance bootstrap | ✅ Done 2026-10-25 |
| P1 | Walking skeleton: service, tests, container, CI | ✅ Done 2026-10-25 |
| P2 | Publish to GHCR | 🚀 In Progress |
| P3 | Security gates and supply chain | ⬜ |
| P4 | Local Kubernetes with kind and Helm | ⬜ |
| P5 | GitOps with Argo CD | ⬜ |
| P6 | Observability: Prometheus and Grafana | ⬜ |
| P7 | Progressive delivery: canary with auto rollback | ⬜ |
| P8 | DORA metrics dashboard | ⬜ |
| P9 | Docs and demo polish | ⬜ |

---

## P0: Governance bootstrap
**Status**: ✅ Done 2026-10-25 — Claude Sonnet 5.5
**Depends On**: none
**Complexity**: Low

### Tasks
| # | Task | Notes |
|---|------|-------|
| 0.1 | `CLAUDE.md`, `HANDOFF.md`, `WORKLOG.md` | contract and session continuity |
| 0.2 | `docs/` plan, decisions, architecture, API | |
| 0.3 | `.gitignore`, `.gitattributes`, `.env.example`, compliance script | |

## P1: Walking skeleton: service, tests, container, CI
**Status**: ✅ Done 2026-10-25 — Claude Sonnet 5.5. Merged via PR #1 with green CI.
**Depends On**: P0
**Complexity**: Medium
Delivered together because each piece is meaningless without the others: a service nobody tests, a container nobody builds, or CI with nothing to run.

### Tasks
| # | Task | Notes |
|---|------|-------|
| 1.1 | FastAPI app: `/`, `/health`, `/version` | version injected at build time |
| 1.2 | pytest suite with coverage gate | 80% minimum |
| 1.3 | Multi-stage Dockerfile | non-root, pinned base, healthcheck |
| 1.4 | `docker-compose.ci.yml` local CI harness | same commands as GitHub |
| 1.5 | `ci.yml`: compliance, lint, tests, image build | no push yet |

## P2: Publish to GHCR
**Status**: 🚀 In Progress — Claude Sonnet 5.5, started 2026-10-25. `publish.yml` merged-pending; done when the first run on `main` pushes and smoke-tests an image.
**Depends On**: P1
**Complexity**: Low
Push images to GHCR on `main` with `GITHUB_TOKEN`; tag with git SHA and `latest`. Needs a remote repo, which the owner must approve.

## P3: Security gates and supply chain
**Status**: ⬜ Not started
**Depends On**: P2
**Complexity**: High
Gitleaks, Semgrep, Trivy (fs and image), CycloneDX SBOM, keyless cosign signing and verification.

## P4: Local Kubernetes with kind and Helm
**Status**: ⬜ Not started
**Depends On**: P2
**Complexity**: Medium
Needs `kind` and `helm` installed. Helm chart for the service.

## P5: GitOps with Argo CD
**Status**: ⬜ Not started
**Depends On**: P4
**Complexity**: High
CI commits the new image tag to the manifests; Argo CD syncs with self-heal.

## P6: Observability
**Status**: ⬜ Not started
**Depends On**: P4
**Complexity**: Medium
`/metrics` endpoint, Prometheus, Grafana dashboard.

## P7: Progressive delivery
**Status**: ⬜ Not started
**Depends On**: P5, P6
**Complexity**: High
Argo Rollouts canary with a Prometheus AnalysisTemplate; a deliberately broken release must roll itself back.

## P8: DORA metrics dashboard
**Status**: ⬜ Not started
**Depends On**: P2
**Complexity**: Medium
Deployment frequency, lead time, change failure rate and recovery time from the GitHub API, published on GitHub Pages. Check DORA's current metric definitions first.

## P9: Docs and demo polish
**Status**: ⬜ Not started
**Depends On**: P7
**Complexity**: Low
README, architecture diagram, screen recording of the rollback, "what I'd do differently".
