# Handoff — updated 2026-10-25 (Claude Sonnet 5.5)
**Branch**: feature/P3-security-gates   **Phase**: P0–P2 done; P3 in progress

## Standing instruction
Owner is away and asked me to keep working unattended: commit often, merge my own PRs once every CI check is green, work through `docs/PLAN.md`. See `CLAUDE.md` for the rules and the "Still needs the owner" list.

## Done
- P0, P1 merged (PR #1, #2 policy). P2 merged (PR #3): `publish.yml` pushes to GHCR; first run green; anonymous `docker pull ghcr.io/amukelani-aj/cicd-showcase:latest` works (package is public).
- P3 on this branch: actions pinned to SHAs, `security.yml`, Trivy image scan and SBOM in `ci.yml`, cosign signing and attestations in `publish.yml`, Dependabot, README verify and security sections, D-007 to D-009.

## In flight
- P3 PR not merged yet. Publish workflow changes can only be proven by running `publish.yml` (use `gh workflow run publish.yml --ref feature/P3-security-gates` before merging, then check the run on `main` after).

## Next steps (ordered)
1. Finish P3: confirm Security workflow and the publish run are green, merge, then verify with `cosign verify` and `gh attestation verify`.
2. P4: install `kind` and `helm` (`winget install Kubernetes.kind Helm.Helm`), write the Helm chart and a cluster bootstrap script.
3. P5 Argo CD, P6 observability, P7 canary rollback, P8 DORA, P9 polish.

## Gotchas
- Venv lives at `%LOCALAPPDATA%\venvs\cicd` (the folder is under OneDrive).
- `gh` has two accounts logged in. Run `gh auth switch --user Amukelani-AJ` first. Commits use the repo-local identity `Amukelani-AJ <125798384+Amukelani-AJ@users.noreply.github.com>`; the global git config is the work identity.
- The shipping helper is in the session scratchpad (`ship.sh`); it is not part of the repo. The manual flow: push, `gh pr create`, `gh pr checks <n> --watch`, `gh pr merge <n> --squash --delete-branch`.
- Tests print a Starlette deprecation warning about `httpx`/`httpx2`. Harmless today.
- Branch protection is not enabled (changing repo settings needs the owner).
