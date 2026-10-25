# Handoff — updated 2026-10-25 (Claude Sonnet 5.5)
**Branch**: feature/P8-dora-metrics   **Phase**: P0–P7 done; P8 in PR

## Standing instruction
Owner is away and asked me to keep working unattended: commit often, merge my own PRs once every CI check is green, work through `docs/PLAN.md`. See `CLAUDE.md` for the rules and the "Still needs the owner" list.

## Done
- P0–P7 merged (PRs #1 to #8). The whole loop works unattended: merge, publish (signed, SBOM, provenance), bot commit of the new tag to `deploy/values.yaml`, Argo CD sync, a canary judged by Prometheus, promotion or automatic rollback. Verified again after the P7 merge: the Git-driven canary promoted `sha-b83b61a` to 5/5 pods.
- P8 (this PR): `dora/` package (five DORA metrics from Publish runs and PRs, stdlib only), 54 tests, `.github/workflows/dora.yml`, `docs/DORA.md`, D-016. Run against the real repo; HTML dashboard rendered and checked.

## Needs the owner
- **GitHub Pages for the DORA dashboard.** Enable Settings > Pages > Source: GitHub Actions, then set the repository variable `ENABLE_PAGES` to `true`. Until then the report is available as the `dora-report` artifact and in each run's summary, and the Pages job is skipped. I did not change repo settings.
- **This PC's clock is about 3m45s ahead of GitHub's** (last successful time sync 2026-10-23 from `Server.MBA.local`). Commit timestamps in this repo are therefore a few minutes in the future, lead times are understated by up to that, and the Docker VM clock looked "behind" because of it. I did not touch the system clock.

## State of the local machine
- kind cluster `cicd` (context `kind-cicd`) running Argo CD v3.5.6, prometheus-stack, argo-rollouts and the `showcase` Application tracking `main`. Service on http://localhost:8088. Port 8080 belongs to an unrelated process (do not kill it).
- The Docker Desktop VM can freeze for minutes while the PC idles; that once rolled back a healthy canary (fixed: no data is now inconclusive and pauses the rollout).
- A Semgrep venv exists at `%LOCALAPPDATA%\venvs\semgrep` (pinned 1.182.1); run the CI scan locally with `semgrep scan --error --metrics off --config p/python --config p/dockerfile --config p/github-actions app dora Dockerfile .github`.

## Next steps (ordered)
1. Confirm the P8 PR merged and the first `DORA metrics` run succeeded (check the run summary).
2. P9: README polish, an architecture diagram, "what I'd do differently" (candidates: feed canary rollbacks back to GitHub so DORA's instability metrics stop being proxies; canary path in CI; branch protection; a real cloud target).
3. Optional: cover the canary path in CI (needs Prometheus and Rollouts on the runner; mind registry throttling, see D-013).

## Gotchas
- Venv lives at `%LOCALAPPDATA%\venvs\cicd` (the folder is under OneDrive).
- `gh` has two accounts logged in. Run `gh auth switch --user Amukelani-AJ` first. Commits use the repo-local identity `Amukelani-AJ <125798384+Amukelani-AJ@users.noreply.github.com>`; the global git config is the work identity.
- New shells need PATH refreshed to find kind and Helm: `$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')`.
- Windows PowerShell 5.1: native stderr becomes an error under `$ErrorActionPreference='Stop'`; use exit codes. `Invoke-RestMethod` to localhost failed here, `curl.exe` works. `scripts/*.ps1` are CRLF (see `.gitattributes`); edit them with line endings normalised.
- The Argo CD manifest sets `imagePullPolicy: Always`, and `public.ecr.aws` throttles GitHub runners: the GitOps e2e job pre-pulls images, falls back to mirrors and patches the policy (D-013).
- The `promote` bot is the only writer allowed to commit directly to `main` (D-012). If branch protection is ever enabled it must be allowed to bypass.
- Grafana's admin password is chart-generated (secret `prometheus-stack-grafana`).
- Semgrep already caught one real finding (shell injection in a workflow). Fix findings, never weaken the gate.
- Very large combined shell commands with several heredocs sometimes fail to parse in this environment; write files with the Write tool or a script file instead.
- The shipping helper (`ship.sh`) is in the session scratchpad, not the repo. Manual flow: push, `gh pr create`, `gh pr checks <n> --watch`, `gh pr merge <n> --squash --delete-branch`.
- Branch protection is not enabled (changing repo settings needs the owner).
