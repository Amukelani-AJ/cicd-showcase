# Worklog

Append-only. One row per commit. Never edit or delete earlier rows.

| Date | AI Assistant | Branch | Description |
|------|--------------|--------|-------------|
| 2026-10-25 | Claude Sonnet 5.5 | main | Bootstrap: CLAUDE.md, plan, decision log, architecture and API docs, compliance script, gitignore |
| 2026-10-25 | Claude Sonnet 5.5 | feature/P1-walking-skeleton | Added FastAPI service (/, /health, /version), 5 tests at 100% coverage, multi-stage non-root Dockerfile, local CI compose harness, ci.yml, README; verified lint, tests and container smoke test locally |
| 2026-10-25 | Claude Sonnet 5.5 | feature/P1-walking-skeleton | Published public repo Amukelani-AJ/cicd-showcase, opened PR #1, first GitHub CI run green; updated handoff and plan |
| 2026-10-25 | Claude Sonnet 5.5 | chore/autonomy-policy | PR #1 merged; recorded owner's standing instruction (commit often, self-merge on green CI, work through the plan) and the "still needs the owner" list in CLAUDE.md |
| 2026-10-25 | Claude Sonnet 5.5 | feature/P2-ghcr-publish | Added publish.yml: build and push to GHCR on main and v* tags (sha, semver, latest tags), smoke-test the pushed digest; logged D-006 |
| 2026-10-25 | Claude Sonnet 5.5 | feature/P3-security-gates | P2 verified (first publish green, anonymous pull works). Pinned all actions to SHAs, added security.yml (Gitleaks, Semgrep, Trivy), Trivy image scan and SBOM in CI, cosign keyless signing, SBOM and provenance attestations in publish, Dependabot; logged D-007 to D-009 |
| 2026-10-25 | Claude Sonnet 5.5 | feature/P3-security-gates | Semgrep caught a real shell-injection pattern in ci.yml (github.base_ref interpolated into run); moved it to an env var instead of weakening the gate |
| 2026-10-25 | Claude Sonnet 5.5 | feature/P4-kind-helm | Installed kind and Helm; added hardened Helm chart, kind config, cluster.ps1 and a k8s CI job (kind + helm install + endpoint check); verified locally with the GHCR image and a local image; logged D-010 (no ingress controller, ingress-nginx retired) and D-011 (port 8088) |
| 2026-10-25 | Claude Sonnet 5.5 | feature/P5-gitops-argocd | Argo CD v3.5.6 Application, deploy/values.yaml, cluster.ps1 gitops action, publish.yml promote job, gitops-e2e.yml; verified locally on kind (Synced/Healthy, manual scale reverted by self-heal in ~5s); logged D-012 |
| 2026-10-25 | Claude Sonnet 5.5 | feature/P5-gitops-argocd | gitops-e2e failed on the runner: argocd-redis (public.ecr.aws) stuck in ImagePullBackOff while the same install worked locally; pre-pull the Argo CD images with retries and side-load into kind, describe pods on failure |
| 2026-10-25 | Claude Sonnet 5.5 | feature/P5-gitops-argocd | Root cause of the e2e failure: public.ecr.aws returns toomanyrequests (Data limit exceeded) to GitHub runners; retries cannot help. Fall back to mirror.gcr.io then docker.io for the redis image, re-tag and side-load; logged D-013 |
| 2026-10-25 | Claude Sonnet 5.5 | feature/P6-observability | P5 verified end to end (first promote commit on main, local Argo CD rolled out sha-f22f668). App: Prometheus metrics middleware and /metrics, FAIL_RATE failure injection, 7 new tests (12 total, 100% coverage), API docs |
