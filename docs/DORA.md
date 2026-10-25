# DORA metrics

How delivery performance is measured in this repo, and how far to trust each number.

The definitions follow [dora.dev/guides/dora-metrics](https://dora.dev/guides/dora-metrics/): five metrics in two groups. MTTR was renamed *failed deployment recovery time* in 2023, and *deployment rework rate* became the fifth metric in 2024.

## Run it

```powershell
python -m dora --repo Amukelani-AJ/cicd-showcase --days 30 --out build/dora   # uses GITHUB_TOKEN, or `gh auth token`
# build/dora/index.html  self-contained dashboard (open it from disk)
# build/dora/report.json the raw numbers
# build/dora/summary.md  the table below
```

The `DORA metrics` workflow does the same daily and after every publish. Each run keeps `dora-report` as an artifact and prints the table in its run summary. Publishing the dashboard on GitHub Pages needs two settings only the repo owner can change: Settings > Pages > Source: **GitHub Actions**, and a repository variable `ENABLE_PAGES` set to `true`. Until then the Pages job is skipped.

## What each metric measures here

A **deployment** is a successful run of the `Publish` workflow on `main`: a merged change that became a signed, published image and a new tag in Git.

| Group | DORA metric | Measured here as | Honest limits |
|---|---|---|---|
| Throughput | Deployment frequency | Successful deployments per day over the window | Accurate for what GitHub can see |
| Throughput | Change lead time | Earliest commit in the PR to the end of its Publish run (median, p90) | Stops at the published image. Argo CD sync and the canary take a few more minutes. Commit timestamps come from the author's clock |
| Throughput | Failed deployment recovery time | A failed Publish run to the next successful one | Pipeline failures only; a canary rollback in the cluster is invisible to GitHub |
| Instability | Change fail rate | Failed Publish runs / all Publish runs | A proxy. A release that Argo Rollouts rolled back still counts as a success |
| Instability | Deployment rework rate | Deployed PRs titled `fix`, `hotfix` or `revert` / deployed PRs | A proxy based on the PR title. DORA defines it as unplanned deployments triggered by an incident |

## Why the instability metrics are proxies

The thing that actually protects users in this project is the canary rollback (see [CANARY_DEMO.md](CANARY_DEMO.md)), and it happens inside the cluster. GitHub never learns that a release was rolled back, so a metric computed only from GitHub cannot see the failures that matter most. The fix is to send rollbacks back to GitHub, for example with Argo Rollouts notifications writing to the GitHub Deployments API, and to count those as failed deployments. That is not built yet (see D-016).

## A real finding: clock skew

While building this, the first report dropped one lead-time sample: PR #3's commits were dated 10:49:22Z, but its deployment finished at 10:47:59Z. A commit cannot be authored after the deployment it caused, so the author's clock was ahead. Measured against GitHub's server time, this machine's clock was **3 minutes 45 seconds ahead**, with its last successful time sync two days earlier. The same drift made the local Docker VM look "behind" and confused an earlier investigation.

The report now counts these samples as skipped and says so on the dashboard instead of dropping them silently. Lead times on this machine are understated by up to the skew.

## Snapshot

Taken on 2026-10-25, before the P8 pull request merged. The repo is a few hours old, so these are illustrations of the output, not trends.

| Group | Metric | Value | Detail |
|---|---|---|---|
| Throughput | Deployment frequency | 0.2/day | 6 successful deployments in 30 days |
| Throughput | Change lead time | 18m 09s | median, first commit to deployment; p90 31m 02s, n=5, 1 skipped (clock skew) |
| Throughput | Failed deployment recovery time | n/a | no failed deployments |
| Instability | Change fail rate | 0% | 0 failed of 6 deployments |
| Instability | Deployment rework rate | 0% | 0 fix or revert PRs of 6 PR deployments |
