# Written by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Demo: ship a good release and a bad one through the canary and watch the automatic rollback
# Modified by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Layer the bad release on the stable one and wait for a healthy rollout at the end (the first run left a canary half-finished)
# Modified by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Only show AnalysisRuns created after a scenario starts, so the previous result is not shown as the current one
<#
.SYNOPSIS
  Drive the canary release on the local kind cluster and narrate what Argo Rollouts decides.
.DESCRIPTION
  Needs the cluster from `./scripts/cluster.ps1 gitops`. Each scenario changes the pod template, which makes
  Argo Rollouts start a canary. The change is applied as an Argo CD Application parameter so the demo needs no
  commits. In real life the same change is a PR to deploy/values.yaml (see the README).
    good: harmless env change -> canary passes both analyses -> promoted to 100%
    bad:  FAIL_RATE=0.6       -> canary returns 500s -> analysis fails -> rollout aborts, stable keeps serving
.EXAMPLE
  ./scripts/demo-canary.ps1                  # good, then bad
  ./scripts/demo-canary.ps1 -Scenario bad
#>
param(
    [ValidateSet('both', 'good', 'bad')][string]$Scenario = 'both',
    [int]$TimeoutMinutes = 8
)

# Windows PowerShell 5.1 turns native stderr into terminating errors under 'Stop'; check exit codes instead.
$ErrorActionPreference = 'Continue'
$Context = 'kind-cicd'
$Rollout = 'showcase-cicd-showcase'
$Scratch = Join-Path $env:TEMP 'cicd-demo-canary'
New-Item -ItemType Directory -Force -Path $Scratch | Out-Null

function Set-ReleaseParams($params) {
    # A JSON merge patch replaces the whole parameters list; $null removes it.
    $body = @{ spec = @{ source = @{ helm = @{ parameters = $params } } } } | ConvertTo-Json -Depth 10 -Compress
    $file = Join-Path $Scratch 'patch.json'
    Set-Content -Path $file -Value $body -Encoding ascii
    kubectl --context $Context -n argocd patch application showcase --type merge --patch-file $file | Out-Null
    kubectl --context $Context -n argocd annotate application showcase argocd.argoproj.io/refresh=hard --overwrite | Out-Null
}

function Get-RolloutJson {
    $json = kubectl --context $Context -n showcase get rollout $Rollout -o json 2>$null
    if ($LASTEXITCODE -eq 0 -and $json) { return ($json | Out-String | ConvertFrom-Json) }
}

# AnalysisRuns that existed before a scenario started belong to earlier rollouts. Hiding them stops the
# previous scenario's result from showing up as if it were the current one. (Names, not timestamps: the
# Docker VM clock can differ from the host's by minutes.)
$script:OldAnalyses = @()

function Get-AnalysisItems {
    $json = kubectl --context $Context -n showcase get analysisrun -o json 2>$null | Out-String
    if (-not $json) { return @() }
    return @(($json | ConvertFrom-Json).items)
}

function Start-Scenario { $script:OldAnalyses = @(Get-AnalysisItems | ForEach-Object { $_.metadata.name }) }

function Get-LatestAnalysis {
    $items = @(Get-AnalysisItems | Where-Object { $script:OldAnalyses -notcontains $_.metadata.name })
    if (-not $items) { return $null }
    return ($items | Sort-Object { $_.metadata.creationTimestamp } | Select-Object -Last 1)
}

function Get-OkShare([int]$Requests = 40) {
    $ok = 0
    foreach ($i in 1..$Requests) {
        $code = curl.exe -s -o NUL -m 2 -w '%{http_code}' http://localhost:8088/
        if ($code -eq '200') { $ok++ }
    }
    return [math]::Round(100 * $ok / $Requests)
}

function Watch-Rollout([string]$Title) {
    Write-Host ""
    Write-Host "=== $Title"
    $deadline = (Get-Date).AddMinutes($TimeoutMinutes)
    $started = $false
    $last = ''
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 5
        $r = Get-RolloutJson
        if (-not $r) { continue }
        $phase = $r.status.phase
        $steps = @($r.spec.strategy.canary.steps).Count
        $step = $r.status.currentStepIndex
        $line = "{0,-12} step {1}/{2}  pods: {3} updated, {4} available of {5}" -f $phase, $step, $steps, $r.status.updatedReplicas, $r.status.availableReplicas, $r.spec.replicas
        $ar = Get-LatestAnalysis
        if ($ar -and $ar.status.phase) {
            $values = @($ar.status.metricResults | ForEach-Object { $_.measurements } | ForEach-Object { $_.value }) -join ', '
            $line += "  | analysis {0}: [{1}]" -f $ar.status.phase, $values
        }
        if ($line -ne $last) { Write-Host ("  {0}  {1}" -f (Get-Date -Format 'HH:mm:ss'), $line); $last = $line }
        if ($phase -in 'Progressing', 'Paused') { $started = $true }
        if ($started -and $phase -in 'Healthy', 'Degraded') {
            if ($r.status.message) { Write-Host "  message: $($r.status.message)" }
            return $phase
        }
    }
    Write-Host "  timed out after $TimeoutMinutes minutes"
    return 'Timeout'
}

function Wait-Healthy([string]$Title) {
    Write-Host ""
    Write-Host "=== $Title"
    $deadline = (Get-Date).AddMinutes($TimeoutMinutes)
    $last = ''
    while ((Get-Date) -lt $deadline) {
        $r = Get-RolloutJson
        if ($r) {
            $line = "{0,-12} step {1}/{2}  pods: {3} updated, {4} available of {5}" -f $r.status.phase, $r.status.currentStepIndex, @($r.spec.strategy.canary.steps).Count, $r.status.updatedReplicas, $r.status.availableReplicas, $r.spec.replicas
            if ($line -ne $last) { Write-Host ("  {0}  {1}" -f (Get-Date -Format 'HH:mm:ss'), $line); $last = $line }
            if ($r.status.phase -eq 'Healthy' -and $r.status.currentStepIndex -eq @($r.spec.strategy.canary.steps).Count) { return 'Healthy' }
        }
        Start-Sleep -Seconds 5
    }
    return 'Timeout'
}

$results = @()
$stable = @() # the parameters that make up the stable release, so a bad release is always layered on top of it

if ($Scenario -in 'both', 'good') {
    Start-Scenario
    $stamp = Get-Date -Format 'HHmmss'
    $stable = @(@{ name = 'env.RELEASE_NOTE'; value = "good-$stamp" })
    Set-ReleaseParams $stable
    $phase = Watch-Rollout "GOOD release (harmless change): the canary should be promoted"
    $results += [pscustomobject]@{ Release = 'good'; Expected = 'Healthy'; Outcome = $phase; OkShare = "$(Get-OkShare)%" }
}

if ($Scenario -in 'both', 'bad') {
    Start-Scenario
    Set-ReleaseParams ($stable + @(@{ name = 'env.FAIL_RATE'; value = '0.6'; forceString = $true }))
    $phase = Watch-Rollout "BAD release (FAIL_RATE=0.6): the canary should be rolled back"
    $results += [pscustomobject]@{ Release = 'bad'; Expected = 'Degraded'; Outcome = $phase; OkShare = "$(Get-OkShare)%" }
    Write-Host ""
    Write-Host "Users kept getting good responses while the canary failed."
}

# Put the Application back to its Git-defined state. After a good release that is one more (passing) canary.
Start-Scenario
Set-ReleaseParams $null
$restored = Wait-Healthy "Restoring the Git-defined release"

Write-Host ""
Write-Host "=== Summary (OkShare = share of 200s on GET / right after the scenario)"
$results | Format-Table -AutoSize | Out-String | Write-Host
$final = Get-RolloutJson
Write-Host "Rollout after cleanup: $($final.status.phase) ($restored)"
