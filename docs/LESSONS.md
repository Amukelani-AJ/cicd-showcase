# What went wrong, and what I would do differently

Everything below happened while building this project. The decision log ([DECISIONS.md](DECISIONS.md)) records what was chosen; this page records what broke and what it taught.

## Things that broke

### My own workflow had a shell-injection pattern (PR #4)

`ci.yml` interpolated `${{ github.base_ref }}` straight into a `run:` command. Semgrep's `run-shell-injection` rule failed the PR and the merge was refused. The value is a branch name, so the real-world risk was small, but the pattern is the classic way GitHub Actions workflows get compromised. The fix was to pass the value through an `env:` variable. I did not weaken or disable the rule.

**Lesson:** a security gate that blocks its own author is working. The gate stayed on and the code changed.

### The GitOps end-to-end job failed three different ways (PRs #6 and #7)

The job installs Argo CD on a fresh kind cluster. The `argocd-redis` pod sat in `ImagePullBackOff`.

1. **First guess:** retry the pull. It failed faster, with `toomanyrequests: Data limit exceeded`: `public.ecr.aws` throttles GitHub's shared runner addresses, and a persistent limit does not yield to retries.
2. **Second fix:** pull the image from a mirror (`mirror.gcr.io`, then `docker.io`), re-tag it, load it into kind. The job passed, and I moved on.
3. **It failed again on the next PR.** The reason: Argo CD's own manifest sets `imagePullPolicy: Always`, so the kubelet ignored the image I had loaded and went back to the throttled registry. The second fix had passed by luck, because that particular pull happened to succeed.
4. **Real fix:** patch the downloaded manifest to `IfNotPresent` in the test job only, so the loaded images are the ones used.

**Lesson:** a fix that passes once is not proven. I should have asked why the pod ignored the loaded image before declaring victory. See D-013.

### A frozen VM rolled back a healthy release (P7)

The canary analysis queries Prometheus three times, 15 seconds apart. In one demo run the third measurement was taken **3 minutes 45 seconds** after the second: the local Docker VM had stalled. When it woke up, Prometheus had no recent samples, the query returned nothing, and my analysis template treated "no data" as a failure. A healthy release was rolled back.

"No evidence" is not the same as "bad evidence". The template now has an explicit failure condition, so an empty or NaN result satisfies neither condition and the measurement is *inconclusive*: the rollout pauses instead of rolling back or promoting. I then re-ran the demo to confirm a clean good release and a clean rollback. See D-015.

**Lesson:** decide what each failure mode of your own signal means before it happens, and test the unhappy path with the real system.

### This machine's clock was 3 minutes 45 seconds fast (P8)

Running the DORA report against the real repository dropped one lead-time sample: PR #3's commits were dated *after* its deployment finished, which is impossible. Comparing a request to GitHub's `Date` header with the local clock showed the PC was 3 minutes 45 seconds ahead, with its last successful time sync two days earlier. Earlier, I had been chasing gaps in Prometheus data and a "lagging" Docker VM; the VM was right and the host was wrong.

The report now counts these samples as skipped and shows the count on the dashboard instead of dropping them without a trace. I did not change the system clock, which is outside this project.

**Lesson:** when timestamps from different systems disagree, check the clocks before theorising about the software. And never drop data silently.

### Documentation I wrote was wrong, or went stale

- I documented Grafana's login as `admin` / `prom-operator` without checking. Trying to log in returned 401. The chart generates a random password into a secret. Corrected in three places.
- A scripted edit of the plan file swallowed a heading and left a stray control character where it had been. I found it only by looking at the output, not from any error.
- Phase statuses (P4 and P5) and the session handoff lagged behind reality for a while.

**Lesson:** verify documented claims against the running system, and review the diff of scripted edits, especially to prose.

### Smaller ones

- **A retired dependency.** Ingress NGINX was retired by Kubernetes SIG Network (best-effort maintenance ended March 2026). I checked before building on it, and exposed the service through a kind port mapping instead (D-010).
- **A busy port.** An unrelated process owns port 8080 on this machine. The cluster uses 8088, and I left the other process alone (D-011).
- **Windows PowerShell 5.1.** It turns a native command's stderr into an error under `$ErrorActionPreference = 'Stop'`, `Invoke-RestMethod` failed against localhost where `curl.exe` worked, and `.ps1` files are CRLF so multi-line edits need care. The scripts use exit codes and `curl.exe`.
- **The trust chain of a scanner.** Trivy had a critical supply-chain advisory in March 2026. I pinned a release published after it, by commit SHA, and recorded the alternative (D-007).

## What I would do differently, and build next

In rough order of value:

1. **Make the cluster enforce signatures.** Images are signed and verified in CI and by anyone with the commands in the runbook, but the cluster does not yet *refuse* an unsigned image. An admission policy (Kyverno `verifyImages` or Sigstore policy-controller) would close that gap.
2. **Send canary rollbacks back to GitHub.** Rollbacks happen in the cluster, so the DORA change fail rate and recovery time are proxies that cannot see the failures that matter most. Argo Rollouts notifications could write to the GitHub Deployments API, which the DORA report could then count.
3. **Cover the canary path in CI.** It is proven by a script and recorded transcripts, but a regression in the analysis template would not fail a PR. It needs Prometheus and Rollouts on the runner, and the registry mirroring from D-013.
4. **Protect `main`.** Branch protection with required checks, and either a bypass for the promotion bot or a promotion that opens and auto-merges a PR. Today the bot is the one writer allowed to commit directly (D-012). This is a repository setting, so it was left for the owner.
5. **Weight the canary by requests, not pods.** Without a traffic router, 20% means one pod of five. Gateway API or a service mesh would make exposure exact.
6. **Pin every Python dependency with hashes.** Direct dependencies are pinned; transitive ones float (D-004). A lock file would fix that.
7. **A real environment.** A cloud target with secrets management, a staging step before production, alert rules (Alertmanager is off locally) and SLO-based analysis. A single failed sample aborting a rollout is right for a demo and too jumpy for real traffic.
8. **Housekeeping for a public repo.** A license (the owner's choice) and contribution notes.
