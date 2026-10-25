# Handoff — updated 2026-10-25 (Claude Sonnet 5.5)
**Branch**: feature/P1-walking-skeleton   **Phase**: P1 — code complete, awaiting first GitHub CI run

## Done this session
- P0 committed on `main` (governance docs, compliance script, repo hygiene files).
- P1 built on the branch: FastAPI service, 5 tests (100% coverage), multi-stage non-root Dockerfile, `docker-compose.ci.yml`, `ci.yml`, README.
- Verified locally: ruff check and format clean; pytest passes on Python 3.14 (host) and 3.12 (Docker CI); image builds (245 MB), runs as uid 10001, `/health` and `/version` respond, container reports healthy.

## In flight / half-finished
- `ci.yml` is untested on GitHub (no remote yet). The `compliance` job uses `--base origin/${{ github.base_ref }}`; confirm it works on the first PR.

## Next steps (ordered)
1. Owner approves creating a GitHub repo and pushing (needs `gh auth status` check first). Open the P1 PR; the owner merges it.
2. P2: publish to GHCR on `main`, tagged with the git SHA.
3. Install `kind` and `helm` before P4 (`winget install Kubernetes.kind Helm.Helm`).

## Gotchas and open questions
- Venv lives at `%LOCALAPPDATA%\venvs\cicd` (the folder is under OneDrive).
- Tests print a Starlette deprecation warning: "Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead." Harmless today; revisit when it becomes an error.
- Python dependencies are pinned for direct packages only (D-004); transitive versions float.
- GitHub Actions use version tags for now; pin to SHAs in P3.
- No compliance run has happened on a PR yet. Locally the script warns if `WORKLOG.md` isn't staged.
