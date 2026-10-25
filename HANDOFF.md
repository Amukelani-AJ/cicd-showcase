# Handoff — updated 2026-10-25 (Claude Sonnet 5.5)
**Branch**: feature/P4-kind-helm   **Phase**: P0–P3 done; P4 in PR

## Standing instruction
Owner is away and asked me to keep working unattended: commit often, merge my own PRs once every CI check is green, work through `docs/PLAN.md`. See `CLAUDE.md` for the rules and the "Still needs the owner" list.

## Done
- P0–P3 merged (PRs #1 to #4). Published image on GHCR is public, signed (cosign keyless), has a CycloneDX SBOM attestation and build provenance; `gh attestation verify` passes from outside CI.
- P4 (this PR): Helm chart `charts/cicd-showcase`, `k8s/kind-config.yaml`, `scripts/cluster.ps1`, a `k8s` CI job that installs the chart on a fresh kind cluster, D-010 and D-011.
- Installed with winget: kind v0.33.0, Helm v4.3.1.

## State of the local machine
- A kind cluster named `cicd` is running (context `kind-cicd`) with release `showcase` deployed from the local image (`image.tag=dev`). Service on http://localhost:8088. Reset with `./scripts/cluster.ps1 up` (GHCR image) or `down`.
- Port 8080 is held by an unrelated process (PID 5812 at the time); do not kill it. That is why the cluster uses 8088.

## Next steps (ordered)
1. Confirm the P4 PR is merged and green; mark P4 done in `docs/PLAN.md`.
2. P5: Argo CD on the kind cluster; CI commits the new image tag to the manifests; self-heal sync.
3. P6 observability, P7 canary rollback, P8 DORA, P9 polish.

## Gotchas
- Venv lives at `%LOCALAPPDATA%\venvs\cicd` (the folder is under OneDrive).
- `gh` has two accounts logged in. Run `gh auth switch --user Amukelani-AJ` first. Commits use the repo-local identity `Amukelani-AJ <125798384+Amukelani-AJ@users.noreply.github.com>`; the global git config is the work identity.
- New shells need the PATH refreshed to find kind and Helm: `$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')`.
- Windows PowerShell 5.1: native stderr becomes an error under `$ErrorActionPreference='Stop'`; use exit codes. `Invoke-RestMethod` to localhost failed here, `curl.exe` works.
- The shipping helper is in the session scratchpad (`ship.sh`), not the repo. Manual flow: push, `gh pr create`, `gh pr checks <n> --watch`, `gh pr merge <n> --squash --delete-branch`.
- Semgrep already caught one real finding (shell injection in a workflow). Fix findings, never weaken the gate.
- Tests print a Starlette deprecation warning about `httpx`/`httpx2`. Harmless today.
- Branch protection is not enabled (changing repo settings needs the owner).
