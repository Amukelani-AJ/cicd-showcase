# Handoff — updated 2026-10-25 (Claude Sonnet 5.5)
**Branch**: feature/P7-canary-rollback   **Phase**: P0–P6 done; P7 in PR

## Standing instruction
Owner is away and asked me to keep working unattended: commit often, merge my own PRs once every CI check is green, work through `docs/PLAN.md`. See `CLAUDE.md` for the rules and the "Still needs the owner" list.

## Done
- P0–P6 merged (PRs #1 to #7). The whole GitOps loop is verified end to end: merge, publish (signed, SBOM, provenance), bot commit of the new tag to `deploy/values.yaml`, Argo CD sync, Prometheus scraping, Grafana dashboard.
- P7 (this PR): Argo Rollouts Application, chart `rollout.yaml` / `analysistemplate.yaml` / `loadgen.yaml` (Rollout only when the CRD exists, else a Deployment from the same pod template), `scripts/demo-canary.ps1`, `docs/CANARY_DEMO.md`, D-015. Proven locally: good release promoted, bad release (`FAIL_RATE=0.6`) aborted on a measured 0.4 to 0.57 success rate while users kept getting 100% good responses.

## State of the local machine
- kind cluster `cicd` (context `kind-cicd`) running Argo CD v3.5.6, prometheus-stack, argo-rollouts and the `showcase` Application, currently tracking branch `feature/P7-canary-rollback`. After the P7 PR merges the branch is deleted, so re-run `./scripts/cluster.ps1 gitops` to point it at `main`.
- Service on http://localhost:8088. Port 8080 belongs to an unrelated process (do not kill it).
- The Docker Desktop VM clock runs a few minutes behind the host and the VM can freeze for minutes while the PC idles; that once rolled back a healthy canary (fixed: no data is now inconclusive).

## Next steps (ordered)
1. Confirm the P7 PR merged and the `Publish` run promoted the new tag; re-point the local cluster at `main`.
2. P8: DORA metrics dashboard from the GitHub API, published on GitHub Pages. Check DORA's current metric definitions first (a 2026 source says there is now a fifth metric, deployment rework rate, and that "MTTR" is outdated wording). Enabling GitHub Pages is a repo settings change, which needs the owner: if blocked, build the report as a workflow artifact and note it here.
3. P9: README polish, architecture diagram, "what I'd do differently".
4. Optional: cover the canary path in CI (needs Prometheus and Rollouts on the runner; mind registry throttling, see D-013).

## Gotchas
- Venv lives at `%LOCALAPPDATA%\venvs\cicd` (the folder is under OneDrive).
- `gh` has two accounts logged in. Run `gh auth switch --user Amukelani-AJ` first. Commits use the repo-local identity `Amukelani-AJ <125798384+Amukelani-AJ@users.noreply.github.com>`; the global git config is the work identity.
- New shells need PATH refreshed to find kind and Helm: `$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')`.
- Windows PowerShell 5.1: native stderr becomes an error under `$ErrorActionPreference='Stop'`; use exit codes. `Invoke-RestMethod` to localhost failed here, `curl.exe` works. `scripts/*.ps1` are CRLF (see `.gitattributes`); edit them with line endings normalised.
- The Argo CD manifest sets `imagePullPolicy: Always`, and `public.ecr.aws` throttles GitHub runners: the GitOps e2e job pre-pulls images, falls back to mirrors and patches the policy (D-013).
- The `promote` bot is the only writer allowed to commit directly to `main` (D-012). If branch protection is ever enabled it must be allowed to bypass.
- Grafana's admin password is chart-generated (secret `prometheus-stack-grafana`).
- Semgrep already caught one real finding (shell injection in a workflow). Fix findings, never weaken the gate.
- The shipping helper (`ship.sh`) is in the session scratchpad, not the repo. Manual flow: push, `gh pr create`, `gh pr checks <n> --watch`, `gh pr merge <n> --squash --delete-branch`.
- Branch protection is not enabled (changing repo settings needs the owner).
