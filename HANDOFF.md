# Handoff — updated 2026-10-25 (Claude Sonnet 5.5)
**Branch**: chore/autonomy-policy   **Phase**: P1 done; P2 next

## Done this session
- P0 and P1 are merged to `main` (PR #1, green CI).
- Repo is public: https://github.com/Amukelani-AJ/cicd-showcase
- Owner left a standing instruction: commit often, merge PRs myself once CI is green, keep working through the plan unattended. Recorded in `CLAUDE.md` with a "Still needs the owner" list.

## In flight / half-finished
- Nothing.

## Next steps (ordered)
1. P2: publish the image to GHCR on `main`, tagged with the git SHA.
2. P3 security gates, P4 kind + Helm, P5 Argo CD, P6 observability, P7 canary rollback, P8 DORA, P9 polish (see `docs/PLAN.md`).

## Gotchas and open questions
- Venv lives at `%LOCALAPPDATA%\venvs\cicd` (the folder is under OneDrive).
- `gh` has two accounts logged in. Run `gh auth switch --user Amukelani-AJ` before any repo operation. Commits use the repo-local identity `Amukelani-AJ <125798384+Amukelani-AJ@users.noreply.github.com>`; the global git config is the work identity and must not be used here.
- Tests print a Starlette deprecation warning about `httpx`/`httpx2`. Harmless today.
- Python dependencies are pinned for direct packages only (D-004).
- GitHub Actions use version tags for now; pin to SHAs in P3.
- `kind`, `helm` and `act` are not installed (needed from P4).
- Branch protection is not enabled (changing repo settings needs the owner).
