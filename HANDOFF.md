# Handoff — updated 2026-10-25 (Claude Sonnet 5.5)
**Branch**: feature/P5-gitops-argocd   **Phase**: P0–P4 done; P5 in PR

## Standing instruction
Owner is away and asked me to keep working unattended: commit often, merge my own PRs once every CI check is green, work through `docs/PLAN.md`. See `CLAUDE.md` for the rules and the "Still needs the owner" list.

## Done
- P0–P4 merged (PRs #1 to #5). Published image on GHCR is public, signed (cosign keyless), has a CycloneDX SBOM attestation and build provenance; `gh attestation verify` passes from outside CI.
- P4: Helm chart, kind config, `scripts/cluster.ps1`, `k8s` CI job, D-010, D-011.
- P5 (this PR): `argocd/application.yaml`, `deploy/values.yaml`, `cluster.ps1 gitops`, a `promote` job in `publish.yml` (bot commits the new tag to `deploy/values.yaml` on main), `gitops-e2e.yml`, D-012.
- Installed with winget: kind v0.33.0, Helm v4.3.1.

## State of the local machine
- A kind cluster named `cicd` is running (context `kind-cicd`) with Argo CD v3.5.6 and the `showcase` Application (currently tracking branch `feature/P5-gitops-argocd`; after merge re-run `./scripts/cluster.ps1 gitops` to track `main`). Service on http://localhost:8088. `down` deletes the cluster.
- Port 8080 is held by an unrelated process (PID 5812 at the time); do not kill it. That is why the cluster uses 8088.

## Next steps (ordered)
1. After the P5 PR merges, watch the first `Publish` run on `main`: the `promote` job must push a `chore(deploy): promote sha-...` commit. This job cannot be tested before merge. If it fails, fix it (check repo Actions permissions and push rejection), then mark P5 done in `docs/PLAN.md`/README.
2. P6 observability (`/metrics`, Prometheus, Grafana), P7 canary rollback (Argo Rollouts), P8 DORA, P9 polish.

## Gotchas
- Venv lives at `%LOCALAPPDATA%envs\cicd` (the folder is under OneDrive).
- `gh` has two accounts logged in. Run `gh auth switch --user Amukelani-AJ` first. Commits use the repo-local identity `Amukelani-AJ <125798384+Amukelani-AJ@users.noreply.github.com>`; the global git config is the work identity.
- New shells need the PATH refreshed to find kind and Helm: `$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')`.
- Windows PowerShell 5.1: native stderr becomes an error under `$ErrorActionPreference='Stop'`; use exit codes. `Invoke-RestMethod` to localhost failed here, `curl.exe` works.
- The shipping helper is in the session scratchpad (`ship.sh`), not the repo. Manual flow: push, `gh pr create`, `gh pr checks <n> --watch`, `gh pr merge <n> --squash --delete-branch`.
- The `promote` bot is the only writer allowed to commit directly to `main` (D-012). If branch protection is ever enabled it must be allowed to bypass.
- Semgrep already caught one real finding (shell injection in a workflow). Fix findings, never weaken the gate.
- Tests print a Starlette deprecation warning about `httpx`/`httpx2`. Harmless today.
- Branch protection is not enabled (changing repo settings needs the owner).
