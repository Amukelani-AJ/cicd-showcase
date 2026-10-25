# Handoff — updated 2026-10-25 (Claude Sonnet 5.5)
**Branch**: feature/P1-walking-skeleton   **Phase**: P1 — code complete, awaiting first GitHub CI run

## Done this session
- P0 committed on `main` (governance docs, compliance script, repo hygiene files).
- P1 built on the branch: FastAPI service, 5 tests (100% coverage), multi-stage non-root Dockerfile, `docker-compose.ci.yml`, `ci.yml`, README.
- Verified locally: ruff check and format clean; pytest passes on Python 3.14 (host) and 3.12 (Docker CI); image builds (245 MB), runs as uid 10001, `/health` and `/version` respond, container reports healthy.

## In flight / half-finished
- PR #1 (https://github.com/Amukelani-AJ/cicd-showcase/pull/1) is open and CI is green (compliance, python, image). Waiting for the owner to squash-merge it.

## Next steps (ordered)
1. Owner merges PR #1. Then `git checkout main && git pull`, and mark P1 done in `docs/PLAN.md`.
2. P2: publish to GHCR on `main`, tagged with the git SHA.
3. Check whether branch protection and required status checks can be enabled on the public repo (they can on public repos); needs the owner's go-ahead.
3. Install `kind` and `helm` before P4 (`winget install Kubernetes.kind Helm.Helm`).

## Gotchas and open questions
- Venv lives at `%LOCALAPPDATA%\venvs\cicd` (the folder is under OneDrive).
- Tests print a Starlette deprecation warning: "Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead." Harmless today; revisit when it becomes an error.
- Python dependencies are pinned for direct packages only (D-004); transitive versions float.
- GitHub Actions use version tags for now; pin to SHAs in P3.
- Repo is public: `Amukelani-AJ/cicd-showcase`. Commits use the repo-local identity `Amukelani-AJ <125798384+Amukelani-AJ@users.noreply.github.com>`; the global git config is the work identity and must not be used here.
- `gh` has two accounts logged in (`Amukelani-AJ`, `Amukelani-MB`). Run `gh auth switch --user Amukelani-AJ` before any repo operation here.
