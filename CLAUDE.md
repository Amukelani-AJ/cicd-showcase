# CI/CD Showcase

A portfolio project demonstrating a complete, free, local-first delivery pipeline: FastAPI service → tests → container image → security gates → GitOps deploy on a local Kubernetes cluster → canary release with automatic rollback → DORA metrics. Owner: Amukelani (solo developer, working with AI assistants). Governance follows the `solo-project-bootstrap` skill.

## Read first
Before any work, read this file, `HANDOFF.md`, the last ~10 rows of `WORKLOG.md`, and the active phase in `docs/PLAN.md`.

## Stack
Python 3.12 (container) / FastAPI / pytest / ruff / Docker / GitHub Actions / GHCR. Later phases: kind, Helm, Argo CD, Argo Rollouts, Prometheus, Grafana. Free and local only: no paid cloud.

## Commands
```powershell
# One-time local setup (venv lives outside OneDrive on purpose)
python -m venv $env:LOCALAPPDATA\venvs\cicd
& $env:LOCALAPPDATA\venvs\cicd\Scripts\pip install -r requirements-dev.txt

# Day to day (use the venv's python)
& $env:LOCALAPPDATA\venvs\cicd\Scripts\python -m pytest
& $env:LOCALAPPDATA\venvs\cicd\Scripts\python -m ruff check .
& $env:LOCALAPPDATA\venvs\cicd\Scripts\python -m ruff format --check .
python scripts/validate-compliance.py

# Run the full CI in Docker, same as GitHub does
docker compose -f docker-compose.ci.yml --profile python run --rm ci-python
docker build -t cicd-showcase:dev .
```

## Conventions
- **Branches**: `main` is protected; no direct commits or force-push. Work on `feature/<slug>`, `bugfix/<slug>`, `fix/<slug>`, `chore/<slug>`, `docs/<slug>`, `hotfix/<slug>`. Land via PR. **The owner merges. Never merge for them.** Squash merge with a conventional-commit title.
- **Attribution**: every code file gets `# Written by Amukelani (<AI model>) on <date> — <what>` and one `# Modified by ...` line per later change. Never delete earlier lines. Use the model that actually did the work.
- **Decisions**: for any non-trivial choice, compare 2–3 options and record it in `docs/DECISIONS.md` before coding.
- **Logging**: append a row to `WORKLOG.md` before every commit; rewrite `HANDOFF.md` at the end of every session; keep `docs/PLAN.md` statuses current.
- **Docs**: keep `docs/ARCHITECTURE.md` and `docs/API_DESIGN.md` in step with the code.
- Lockfiles and pinned versions are committed. Pin GitHub Actions to full commit SHAs.

## Prohibited
Merging PRs; pushing secrets; committing `.env`, `node_modules/`, `__pycache__/`, `.venv/`; working without reading the files above; deleting attribution lines; pushing to a remote, creating remote repos or publishing images without the owner's go-ahead in that session.

## Pre-commit checklist
1. On a feature branch, not `main`.
2. `python scripts/validate-compliance.py` passes.
3. `ruff check`, `ruff format --check` and `pytest` pass (locally or in Docker).
4. No secrets or `.env` staged.
5. Attribution headers on new or modified files.
6. Decision logged for any non-trivial choice.
7. Architecture/API docs updated if affected.
8. `WORKLOG.md` row appended; `HANDOFF.md` rewritten; `docs/PLAN.md` updated.

## Background tasks
Never fire and forget. Keep the container/task ID, check `docker logs --tail 50 <id>`, and treat output that hasn't advanced for 1–2 minutes as stuck. Timeouts: lint/tests 3 min, builds 15 min, E2E 10 min. Reap stale tasks (`docker kill`, `docker rm -f`) and verify exit codes (`docker inspect <id> --format='{{.State.ExitCode}}'`).

## Environment notes
- The folder is under OneDrive. Keep `.venv`, `node_modules` and build output out of it; use the venv path above.
- If GitHub, a registry or a tool blocks an action or asks for credentials, tell the owner before trying workarounds.
