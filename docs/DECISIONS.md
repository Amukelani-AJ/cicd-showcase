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
