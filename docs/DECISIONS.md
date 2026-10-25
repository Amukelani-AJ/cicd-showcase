# Decision log

Append-only. Superseded decisions stay; add a new entry that supersedes them.

## D-001: Application language and framework (2026-10-25)
**Options**: FastAPI (Python) · Express (Node) · Flask (Python)
**Constraints**: owner is comfortable with Python or Node; need `/metrics` and typed request/response models; small, fast tests; first-class OpenAPI docs
**Decision**: FastAPI. Built-in OpenAPI, Pydantic validation, easy `/metrics` via a Prometheus client, `TestClient` for fast tests.
**Trade-offs**: more dependencies than Flask; Python image is larger than Node alpine.
**Status**: Accepted

## D-002: Container registry (2026-10-25)
**Options**: GHCR · Docker Hub · local `kind` registry only
**Constraints**: free; no extra account; works with `GITHUB_TOKEN`; supports cosign and attestations
**Decision**: GHCR for published images; a local registry or `kind load` for the in-cluster loop where convenient.
**Trade-offs**: needs a GitHub remote, which the owner must approve.
**Status**: Accepted

## D-003: Local Kubernetes runtime (2026-10-25)
**Options**: kind · minikube · k3d · Docker Desktop's built-in Kubernetes
**Constraints**: free; reproducible from a script on Windows; easy to destroy and recreate; usable in CI
**Decision**: kind (reproducible multi-node clusters from a config file, used in the Argo CD docs and in CI).
**Trade-offs**: no built-in LoadBalancer (use ingress with port mappings). Needs `kind` installed.
**Status**: Accepted

## D-004: Python dependency management (2026-10-25)
**Options**: pip + pinned `requirements*.txt` · uv with `uv.lock` · Poetry
**Constraints**: simple to read in a portfolio repo; identical in Docker and CI; no extra tooling to install
**Decision**: pip with exact pins in `requirements.txt` and `requirements-dev.txt`.
**Trade-offs**: no hash locking or transitive-dependency resolution. Revisit with uv if the dependency set grows.
**Status**: Accepted

## D-005: Merge strategy (2026-10-25)
**Options**: squash · merge commit · rebase
**Constraints**: solo developer; readable history; each PR is one coherent change
**Decision**: squash merge with a conventional-commit title.
**Trade-offs**: individual branch commits are lost after merge.
**Status**: Accepted

## D-006: When to publish images (2026-10-25)
**Options**: every PR · every push to `main` plus `v*` tags · tags only
**Constraints**: GHCR storage is free but finite; PR images from forks must never get registry write access; GitOps (P5) needs an image for every merged change
**Decision**: publish on push to `main` (tags `sha-<short>` and `latest`) and on `v*` tags (semver tags). PRs only build and smoke-test, never push.
**Trade-offs**: no per-PR images; preview environments would need a separate decision.
**Status**: Accepted

## D-007: Vulnerability scanner and action-pinning policy (2026-10-25)
**Options**: Trivy · Grype (Anchore) · Docker Scout
**Constraints**: free; scans dependencies, container images and Dockerfile/workflow config; usable in GitHub Actions and locally; trustworthy supply chain. Trivy had a critical advisory on 2026-03-21 ("Trivy ecosystem supply chain temporarily compromised"), and `trivy-action` a medium one on 2026-02-18.
**Decision**: Trivy, using `aquasecurity/trivy-action` v0.36.0 (released 2026-04-22, after the incident), pinned by full commit SHA. Every other action is also SHA-pinned, and Dependabot proposes updates.
**Trade-offs**: a compromised upstream tag can no longer change what runs, but SHA pins go stale without Dependabot. Revisit and switch to Grype (pairs with Syft) if another incident hits Trivy.
**Status**: Accepted

## D-008: Image signing and attestations (2026-10-25)
**Options**: cosign keyless (OIDC) · cosign with a stored key · GitHub artifact attestations only · Notation
**Constraints**: free; no long-lived signing key to store or leak; verifiable by anyone; works with GHCR
**Decision**: cosign keyless for the image signature and a CycloneDX SBOM attestation, plus a GitHub build provenance attestation (`actions/attest-build-provenance`). The publish workflow verifies its own signature and SBOM attestation after signing.
**Trade-offs**: signing identities are recorded in the public Sigstore transparency log, which is fine for a public repo. No SLSA level is claimed: that needs checking against the SLSA spec.
**Status**: Accepted

## D-009: SAST tool (2026-10-25)
**Options**: Semgrep OSS · CodeQL · Bandit
**Constraints**: free; covers Python plus Dockerfile and GitHub Actions rules; pinned version; no repo-settings changes needed
**Decision**: Semgrep OSS pinned to 1.182.1 with `p/python`, `p/dockerfile` and `p/github-actions` rule packs.
**Trade-offs**: shallower dataflow analysis than CodeQL. CodeQL's default setup could be added later, but that is a repo setting that needs the owner.
**Status**: Accepted

## D-010: How traffic reaches the local cluster (2026-10-25)
**Options**: ingress-nginx · Traefik or another ingress controller · Gateway API · NodePort with a kind port mapping
**Constraints**: free; minimal moving parts; must stay maintained. Ingress NGINX was retired by Kubernetes SIG Network (announced 2025-11-11, best-effort maintenance ended March 2026), so new work should not build on it.
**Decision**: no ingress controller. The chart exposes a NodePort (30080) and `k8s/kind-config.yaml` maps it to `127.0.0.1:8088`. Bound to loopback so the demo is never reachable from the network.
**Trade-offs**: no host or path routing and no weighted traffic splitting at the edge. Argo Rollouts canaries in P7 will use replica-based weighting; revisit with Gateway API or Traefik only if request-weighted traffic splitting is needed.
**Status**: Accepted

## D-011: Host port 8088 (2026-10-25)
**Options**: 8080 · 8088 · a random free port
**Constraints**: 8080 is held by an unrelated process on the dev machine (bind fails with a permissions error); the port must be stable so docs and scripts can rely on it
**Decision**: 8088, unreserved on this machine. If it clashes elsewhere, change `hostPort` in `k8s/kind-config.yaml` and the three references in `scripts/cluster.ps1` and the chart NOTES.
**Trade-offs**: a non-default port to remember.
**Status**: Accepted

## D-012: GitOps promotion mechanism and Argo CD version (2026-10-25)
**Options**: (a) CI commits the new image tag to `deploy/values.yaml` in this repo · (b) a separate environment repo · (c) Argo CD Image Updater · (d) CI opens a PR for the tag bump and auto-merges it
**Constraints**: free; only this repo may be used; no PATs or other stored secrets (`GITHUB_TOKEN` only); the promotion must not retrigger itself; Git must stay the single source of truth for what runs
**Decision**: (a). After a verified publish, `publish.yml` rewrites `image.tag` in `deploy/values.yaml` with one commit by `github-actions[bot]`. Commits pushed with `GITHUB_TOKEN` do not trigger workflows, so there is no loop. Argo CD (pinned to v3.5.6; v3.5.4 and later contain the fixes for the three critical repo-server advisories published 2026-10-07) tracks `main` over HTTPS with no credentials because the repo is public, and syncs automatically with prune and self-heal.
**Trade-offs**: the bot is the one writer allowed to commit directly to `main`, limited to the tag line in `deploy/values.yaml`. If branch protection is enabled later, the bot must be allowed to bypass it, or this should move to option (d). Argo CD polls every 3 minutes by default; a webhook would make it instant but needs a reachable endpoint. Concurrent merges are serialised by a concurrency group, but an out-of-order run could briefly promote an older tag.
**Status**: Accepted

## D-013: Image sources in the GitOps e2e job (2026-10-25)
**Options**: pull from the manifest's registries only · authenticate to each registry · fall back to mirrors of the same official image
**Constraints**: free; no registry credentials or secrets; the job must not be flaky. `public.ecr.aws` answered GitHub runners with `toomanyrequests: Data limit exceeded` (persistent, so retries do not help); the same pull works from a home IP.
**Decision**: the job pre-pulls every image in the Argo CD manifest. For `public.ecr.aws/docker/library/*` it falls back to `mirror.gcr.io/library/*`, then `docker.io/library/*`, re-tags the result to the original name and side-loads it into kind. Argo CD itself and the manifest stay untouched.
**Trade-offs**: the test may run a byte-identical copy of the image from a mirror rather than ECR; tags are mutable, so this relies on the official image tag. Real clusters installing Argo CD are unaffected.
**Status**: Accepted
