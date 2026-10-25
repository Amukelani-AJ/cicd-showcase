# Runbook

Commands, ports, credentials and fixes for running this project locally. PowerShell on Windows. Anything that talks to the cluster uses the `kind-cicd` context explicitly.

## Prerequisites

Docker Desktop, `git`, Python 3.12+, [kind](https://kind.sigs.k8s.io/) and [Helm](https://helm.sh/):

```powershell
winget install Kubernetes.kind Helm.Helm
# a new shell picks up the PATH change; in an existing one:
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
```

Local development uses a virtual environment outside any synced folder (OneDrive would sync it):

```powershell
python -m venv $env:LOCALAPPDATA\venvs\cicd
& $env:LOCALAPPDATA\venvs\cicd\Scripts\pip install -r requirements-dev.txt
& $env:LOCALAPPDATA\venvs\cicd\Scripts\python -m pytest
```

## The cluster

```powershell
./scripts/cluster.ps1 gitops                 # kind + Argo CD + Prometheus/Grafana + Argo Rollouts + the app (about 5 minutes)
./scripts/cluster.ps1 gitops -NoPlatform     # Argo CD and the app only
./scripts/cluster.ps1 gitops -Revision my-branch   # track a branch instead of main
./scripts/cluster.ps1 up                     # no GitOps: install the chart directly with Helm
./scripts/cluster.ps1 up -Local              # same, building and loading your local Dockerfile
./scripts/cluster.ps1 status
./scripts/cluster.ps1 down                   # deletes the cluster
```

The service listens on <http://localhost:8088> (bound to `127.0.0.1` only).

## Web UIs

| UI | Command | Address | Login |
|---|---|---|---|
| Argo CD | `kubectl --context kind-cicd -n argocd port-forward svc/argocd-server 8089:443` | https://localhost:8089 | `admin` and the secret below |
| Grafana | `kubectl --context kind-cicd -n monitoring port-forward svc/prometheus-stack-grafana 3000:80` | http://localhost:3000 | `admin` and the secret below |
| Prometheus | `kubectl --context kind-cicd -n monitoring port-forward svc/prometheus-stack-kube-prom-prometheus 9090` | http://localhost:9090 | none |
| Rollouts | `kubectl --context kind-cicd -n argo-rollouts port-forward svc/argo-rollouts-dashboard 3100` | http://localhost:3100 | none |

Passwords are generated per cluster; read and base64-decode them:

```powershell
kubectl --context kind-cicd -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"
kubectl --context kind-cicd -n monitoring get secret prometheus-stack-grafana -o jsonpath="{.data.admin-password}"
```

## Releasing

Merging to `main` is the release. In order: the `Publish` workflow builds the image, smoke-tests it, signs it, attaches the SBOM and provenance, and verifies them; a `promote` job commits the new `sha-<short>` tag to `deploy/values.yaml`; Argo CD syncs; Argo Rollouts runs the canary.

Watch a canary, or force a good and a bad one:

```powershell
kubectl --context kind-cicd -n showcase get rollout showcase-cicd-showcase -w
./scripts/demo-canary.ps1                    # good release, then a bad one, then restore (about 12 minutes)
./scripts/demo-canary.ps1 -Scenario bad      # just the rollback (about 2 minutes)
```

To ship a bad change for real, edit `env` in `deploy/values.yaml` (for example `FAIL_RATE: "0.6"`) in a PR. After the merge the canary is judged and rolled back, and Argo CD reports the app **Degraded** until the commit is reverted.

An analysis with no data (no traffic, a scrape gap) pauses the rollout instead of rolling back or promoting. Fix the cause (usually a stalled node or no traffic) and let a new analysis run, or promote or abort it from the Rollouts dashboard. The `kubectl argo rollouts` plugin does the same but is not installed here.

## Verifying a published image

```powershell
docker pull ghcr.io/amukelani-aj/cicd-showcase:latest

cosign verify ghcr.io/amukelani-aj/cicd-showcase:latest `
  --certificate-identity-regexp '^https://github.com/Amukelani-AJ/cicd-showcase/\.github/workflows/publish\.yml@refs/(heads/main|tags/v.*)$' `
  --certificate-oidc-issuer https://token.actions.githubusercontent.com

gh attestation verify oci://ghcr.io/amukelani-aj/cicd-showcase:latest --repo Amukelani-AJ/cicd-showcase
```

## DORA report

```powershell
python -m dora --repo Amukelani-AJ/cicd-showcase --days 30 --out build/dora
```

Uses `GITHUB_TOKEN`, or the active `gh` account. The scheduled workflow publishes the same report as an artifact and run summary. To also publish it on GitHub Pages, enable Settings > Pages > Source: GitHub Actions and set the repository variable `ENABLE_PAGES` to `true`.

## Running the CI checks locally

```powershell
docker compose -f docker-compose.ci.yml --profile python run --rm ci-python     # lint, format, tests
python scripts/validate-compliance.py                                           # branch and hygiene rules
```

Semgrep with the same pinned version and rules as CI:

```powershell
python -m venv $env:LOCALAPPDATA\venvs\semgrep
& $env:LOCALAPPDATA\venvs\semgrep\Scripts\pip install semgrep==1.182.1
& $env:LOCALAPPDATA\venvs\semgrep\Scripts\semgrep scan --error --metrics off --config p/python --config p/dockerfile --config p/github-actions app dora Dockerfile .github
```

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `kind create cluster` fails with "ports are not available: 127.0.0.1:8080" | Something else owns the port. The cluster maps the service to **8088** for this reason. Check `Get-NetTCPConnection -State Listen -LocalPort 8088`; change `hostPort` in `k8s/kind-config.yaml` and the references in `scripts/cluster.ps1` if 8088 is taken too. Do not kill an unrelated process |
| A script fails with a red "NativeCommandError" although the command worked | Windows PowerShell 5.1 turns native stderr into an error under `$ErrorActionPreference = 'Stop'`. The scripts use exit codes instead; keep it that way when editing |
| `Invoke-RestMethod` to localhost fails but a browser works | Use `curl.exe`. The scripts do |
| Argo CD shows the app `Synced` but the new files are not there yet | Argo polls every 3 minutes. Force it: `kubectl --context kind-cicd -n argocd annotate application showcase argocd.argoproj.io/refresh=hard --overwrite` |
| The canary rolled back a healthy release | Check the AnalysisRun: `kubectl --context kind-cicd -n showcase get analysisrun -o yaml`. Look at the measurement timestamps. A frozen Docker VM once produced a gap in the data (now inconclusive, which pauses instead of rolling back) |
| Timestamps disagree between the PC, the cluster and GitHub | This PC's clock has drifted (3 minutes 45 seconds ahead on 2026-10-25). Compare `date -u` with `curl -sI https://api.github.com` (the `Date` header) and resync Windows time |
| The GitOps e2e job fails with `ImagePullBackOff` on redis | The job pre-pulls images and patches `imagePullPolicy`, because `public.ecr.aws` throttles GitHub runners (D-013). If it recurs, look at the pre-pull step's log |
| `scripts/*.ps1` show as modified after a checkout | They are CRLF on purpose (`.gitattributes`). Edit them with line endings preserved |
