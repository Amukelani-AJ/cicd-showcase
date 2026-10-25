# Handoff — updated 2026-10-25 (Claude Sonnet 5.5)
**Branch**: feature/P9-polish   **Phase**: all of P0 to P9 done; this PR is the last one

## Standing instruction
The owner was away and asked me to keep working unattended: commit often, merge my own PRs once every CI check is green, work through `docs/PLAN.md`. That plan is now complete. See `CLAUDE.md` for the rules and the "Still needs the owner" list.

## Done
- P0 to P9. Public repo `Amukelani-AJ/cicd-showcase`. PRs #1 to #9 merged with green CI, this one is #10. The README is the front page; `docs/RUNBOOK.md` has every command; `docs/LESSONS.md` is the honest account of what broke.
- The loop works unattended and was verified more than once: merge, publish (signed, SBOM, provenance), bot commit of the new tag to `deploy/values.yaml`, Argo CD sync, Prometheus-judged canary, promotion or automatic rollback, DORA report.

## Needs the owner (nothing blocks the project; these are your decisions)
1. **GitHub Pages for the DORA dashboard.** Enable Settings > Pages > Source: GitHub Actions, then set the repository variable `ENABLE_PAGES` to `true`. Until then the report is the `dora-report` artifact and the run summary, and the Pages job is skipped.
2. **A LICENSE file.** The repo is public and has none. Choosing a license is yours, so I did not add one.
3. **Branch protection on `main`** with the CI checks as required. If you enable it, allow `github-actions[bot]` to bypass, or the `promote` job (D-012) will fail to push the tag. See `docs/LESSONS.md` for the alternative.
4. **This PC's clock is about 3m45s ahead of GitHub's** (last successful sync 2026-10-23 from `Server.MBA.local`). It skews commit timestamps and understates DORA lead time. I did not touch the system clock.
5. **Which GitHub account.** Everything lives under `Amukelani-AJ` (personal). The work account `Amukelani-MB` was never used. `gh` still has both logged in.

## State of the local machine
- kind cluster `cicd` (context `kind-cicd`) is running Argo CD v3.5.6, prometheus-stack, argo-rollouts and the `showcase` Application tracking `main`. Service on http://localhost:8088. `./scripts/cluster.ps1 down` deletes it. It uses a fair amount of memory; delete it if you do not need it.
- Port 8080 belongs to an unrelated process (I did not touch it), hence 8088.
- Venvs outside OneDrive: `%LOCALAPPDATA%\venvs\cicd` (project) and `%LOCALAPPDATA%\venvs\semgrep` (pinned Semgrep).
- kind v0.33.0 and Helm v4.3.1 were installed with winget.

## If you want to keep going
See "What I would do differently" in `docs/LESSONS.md`. Highest value first: enforce signatures at admission, feed canary rollbacks back to GitHub so the DORA instability metrics stop being proxies, and cover the canary path in CI.

## Gotchas
- `gh` has two accounts logged in. Run `gh auth switch --user Amukelani-AJ` first. Commits use the repo-local identity `Amukelani-AJ <125798384+Amukelani-AJ@users.noreply.github.com>`; the global git config is the work identity.
- New shells need PATH refreshed to find kind and Helm: `$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')`.
- Windows PowerShell 5.1: native stderr becomes an error under `$ErrorActionPreference='Stop'`; use exit codes. `Invoke-RestMethod` to localhost failed here, `curl.exe` works. `scripts/*.ps1` are CRLF (see `.gitattributes`); edit them with line endings preserved.
- The Argo CD manifest sets `imagePullPolicy: Always`, and `public.ecr.aws` throttles GitHub runners: the GitOps e2e job pre-pulls images, falls back to mirrors and patches the policy (D-013).
- The `promote` bot is the only writer allowed to commit directly to `main` (D-012).
- Grafana's admin password is chart-generated (secret `prometheus-stack-grafana`).
- Semgrep already caught one real finding (shell injection in a workflow). Fix findings, never weaken the gate.
- Very large combined shell commands with several heredocs sometimes fail to parse in this environment; write files with the Write tool or a script file instead.
- The shipping helper (`ship.sh`) was in the session scratchpad, not the repo. Manual flow: push, `gh pr create`, `gh pr checks <n> --watch`, `gh pr merge <n> --squash --delete-branch`.
