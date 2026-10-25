# Written by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Create, inspect and delete the local kind cluster and deploy the Helm chart
# Modified by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Use exit codes instead of 'Stop' so PS 5.1 does not treat native stderr as an error
# Modified by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Host port 8088 (8080 is taken on this machine)
# Modified by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Probe with curl.exe instead of Invoke-RestMethod
# Modified by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Quote the resource list so PowerShell does not split it on commas
# Modified by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Added the gitops action: install Argo CD v3.5.6 and apply the Application
# Modified by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — gitops: wait on workloads, not pods; add -Revision to track a branch
<#
.SYNOPSIS
  Manage the local kind cluster for this project.
.EXAMPLE
  ./scripts/cluster.ps1 up                 # cluster + chart using the published GHCR image (latest)
  ./scripts/cluster.ps1 up -Tag sha-1a2b3c4
  ./scripts/cluster.ps1 up -Local          # build the local Dockerfile and load it into the cluster
  ./scripts/cluster.ps1 gitops             # cluster + Argo CD; Argo CD deploys the chart from Git (replaces `up`)
  ./scripts/cluster.ps1 gitops -Revision my-branch   # track a branch or commit instead of main
  ./scripts/cluster.ps1 status
  ./scripts/cluster.ps1 down
.NOTES
  Every kubectl/helm call is pinned to the kind-cicd context so no other cluster is ever touched.
#>
param(
    [Parameter(Mandatory)][ValidateSet('up', 'gitops', 'down', 'status')][string]$Action,
    [string]$Tag = 'latest',
    [string]$Revision = '', # gitops: track this branch or commit instead of main (testing unmerged changes)
    [switch]$Local
)

# Windows PowerShell 5.1 turns native stderr (kind, helm and docker log progress there) into
# terminating errors under 'Stop', so failures are detected through $LASTEXITCODE instead.
$ErrorActionPreference = 'Continue'
$Cluster = 'cicd'
$Context = "kind-$Cluster"
$Release = 'showcase'
# Pinned: v3.5.4+ contains the fixes for the 2026-10-07 repo-server advisories (see D-012).
$ArgoVersion = 'v3.5.6'
$ArgoInstallUrl = "https://raw.githubusercontent.com/argoproj/argo-cd/$ArgoVersion/manifests/install.yaml"
$Root = Split-Path -Parent $PSScriptRoot

function Test-Cluster { (@(kind get clusters 2>&1) | ForEach-Object { "$_" }) -contains $Cluster }

# curl.exe (ships with Windows 10+) instead of Invoke-RestMethod: PS 5.1's cmdlet failed against
# localhost here while curl succeeded, most likely because of system proxy handling.
function Wait-Http([string]$Url, [int]$Seconds = 30) {
    foreach ($i in 1..$Seconds) {
        $body = curl.exe -fsS -m 2 $Url 2>$null
        if ($LASTEXITCODE -eq 0 -and $body) { return $body | ConvertFrom-Json }
        Start-Sleep -Seconds 1
    }
    throw "No response from $Url after $Seconds s"
}

switch ($Action) {
    'up' {
        if (-not (Test-Cluster)) {
            kind create cluster --config "$Root/k8s/kind-config.yaml"
            if ($LASTEXITCODE -ne 0) { throw 'kind create cluster failed' }
        } else {
            Write-Host "Cluster '$Cluster' already exists"
        }

        $values = @('--set', "image.tag=$Tag")
        if ($Local) {
            docker build -t cicd-showcase:dev -f "$Root/Dockerfile" $Root
            if ($LASTEXITCODE -ne 0) { throw 'docker build failed' }
            kind load docker-image cicd-showcase:dev --name $Cluster
            if ($LASTEXITCODE -ne 0) { throw 'kind load failed' }
            $values = @('--set', 'image.repository=cicd-showcase', '--set', 'image.tag=dev', '--set', 'image.pullPolicy=Never')
        }

        helm upgrade --install $Release "$Root/charts/cicd-showcase" --kube-context $Context @values --wait --timeout 180s
        if ($LASTEXITCODE -ne 0) { throw 'helm upgrade failed' }

        Write-Host 'GET http://localhost:8088/version ->' (Wait-Http 'http://localhost:8088/version' | ConvertTo-Json -Compress)
    }
    'status' {
        if (-not (Test-Cluster)) { Write-Host "Cluster '$Cluster' does not exist"; return }
        kubectl --context $Context get 'nodes,pods,svc' -A -o wide
        kubectl --context $Context get applications -n argocd 2>&1 | ForEach-Object { "$_" }
        Write-Host 'GET http://localhost:8088/version ->' (Wait-Http 'http://localhost:8088/version' 5 | ConvertTo-Json -Compress)
    }
    'gitops' {
        if (-not (Test-Cluster)) {
            kind create cluster --config "$Root/k8s/kind-config.yaml"
            if ($LASTEXITCODE -ne 0) { throw 'kind create cluster failed' }
        }

        # Argo CD becomes the only thing that deploys the app, so drop a direct Helm release if `up` made one.
        helm uninstall $Release --kube-context $Context 2>&1 | Out-Null

        kubectl --context $Context create namespace argocd --dry-run=client -o yaml | kubectl --context $Context apply -f -
        # Server-side apply: the ApplicationSet CRD is too large for client-side apply.
        kubectl --context $Context apply --server-side --force-conflicts -n argocd -f $ArgoInstallUrl
        if ($LASTEXITCODE -ne 0) { throw 'Argo CD install failed' }
        # Wait on the workloads, not on pods: pods do not exist yet right after the apply.
        kubectl --context $Context wait --for=condition=Available deployment --all -n argocd --timeout=300s
        if ($LASTEXITCODE -ne 0) { throw 'Argo CD deployments did not become available' }
        kubectl --context $Context rollout status statefulset/argocd-application-controller -n argocd --timeout=300s
        if ($LASTEXITCODE -ne 0) { throw 'Argo CD application controller did not become ready' }

        $manifest = Get-Content "$Root/argocd/application.yaml" -Raw
        if ($Revision) { $manifest = $manifest -replace 'targetRevision: main', "targetRevision: $Revision" }
        $manifest | kubectl --context $Context apply -f -
        if ($LASTEXITCODE -ne 0) { throw 'Applying the Application failed' }

        $state = ''
        foreach ($i in 1..60) {
            $state = (kubectl --context $Context get application $Release -n argocd -o 'jsonpath={.status.sync.status}/{.status.health.status}' 2>$null)
            if ($state -eq 'Synced/Healthy') { break }
            Start-Sleep -Seconds 5
        }
        Write-Host "Application $Release is $state"
        if ($state -ne 'Synced/Healthy') { throw 'Argo CD did not reach Synced/Healthy within 5 minutes' }
        Write-Host 'GET http://localhost:8088/version ->' (Wait-Http 'http://localhost:8088/version' | ConvertTo-Json -Compress)
    }
    'down' {
        if (Test-Cluster) { kind delete cluster --name $Cluster } else { Write-Host "Cluster '$Cluster' does not exist" }
    }
}
