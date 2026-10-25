# Canary demo: transcripts

Real output of [scripts/demo-canary.ps1](../scripts/demo-canary.ps1) on the local kind cluster (2026-10-25). Times are the host's local time. Nothing is edited except the two omitted rows noted below.

How to read a line: `step N/7` is the position in the canary plan (`setWeight 20`, pause, analysis, `setWeight 60`, pause, analysis, `setWeight 100`). `pods` counts pods running the new revision. `analysis` shows each Prometheus measurement of the canary pods' success rate on `GET /`; `[1]` means 100% of requests succeeded.

## A good release is promoted

A harmless pod-template change. Both analyses pass (3 of 3 measurements at 100%), the canary grows from 1 pod to 3 to 5, and the rollout finishes in about three minutes.

```text
=== GOOD release (harmless change): the canary should be promoted
  14:23:47  Progressing  step 2/7  pods: 1 updated, 5 available of 5  | analysis Running: [[1]]
  14:23:59  Progressing  step 2/7  pods: 1 updated, 5 available of 5  | analysis Running: [[1], [1]]
  14:24:15  Progressing  step 3/7  pods: 3 updated, 4 available of 5  | analysis Successful: [[1], [1], [1]]
  14:24:21  Paused       step 4/7  pods: 3 updated, 5 available of 5  | analysis Successful: [[1], [1], [1]]
  14:25:05  Progressing  step 5/7  pods: 3 updated, 5 available of 5  | analysis Running: [[1]]
  14:25:22  Progressing  step 5/7  pods: 3 updated, 5 available of 5  | analysis Running: [[1], [1]]
  14:25:33  Progressing  step 5/7  pods: 3 updated, 5 available of 5  | analysis Successful: [[1], [1], [1]]
  14:25:39  Progressing  step 6/7  pods: 5 updated, 4 available of 5  | analysis Successful: [[1], [1], [1]]
  14:25:44  Healthy      step 7/7  pods: 5 updated, 5 available of 5  | analysis Successful: [[1], [1], [1]]
```

Two rows at the start of this run are left out (steps 0 and 1). The script displayed the previous run's analysis result on them, which was a display bug in the script, not in the rollout. It has been fixed: the script now ignores analyses that existed before the scenario began.

## A bad release is rolled back automatically

`FAIL_RATE=0.6` makes `GET /` fail for 60% of requests. The canary gets one pod out of five. About 45 seconds after it starts, the first analysis measures a success rate of 0.4, far below the 0.95 threshold, and the rollout aborts. The canary pod is removed and the stable revision keeps serving. Right after the abort, 100% of sampled requests to `GET /` succeed.

```text
=== BAD release (FAIL_RATE=0.6): the canary should be rolled back
  14:30:41  Progressing  step 0/7  pods: 1 updated, 4 available of 5
  14:30:53  Paused       step 1/7  pods: 1 updated, 5 available of 5
  14:31:37  Degraded     step 0/7  pods:  updated, 4 available of 5  | analysis Failed: [[0.4]]
  message: RolloutAborted: Rollout aborted update to revision 11: Step-based analysis phase error/failed: Metric "canary-success-rate" assessed Failed due to failed (1) > failureLimit (0)

Users kept getting good responses while the canary failed.

=== Restoring the Git-defined release
  14:31:49  Degraded     step 0/7  pods:  updated, 5 available of 5
  14:31:54  Healthy      step 7/7  pods: 5 updated, 5 available of 5
```

Other runs of the same scenario measured 0.44, 0.48 and 0.57. The success rate varies because `FAIL_RATE` is random, but every run was far below the threshold.

In a real setup the bad change is a commit. Git keeps saying "v2" while the cluster keeps serving v1, so Argo CD reports the app **Degraded** until the commit is reverted. That is deliberate: the cluster protects users, and a human fixes the source of truth.

## What the first runs taught

The first version of the analysis treated an empty Prometheus result as a failure. In one run the local Docker VM froze for almost four minutes in the middle of an analysis; when it woke up Prometheus had no recent samples, the measurement came back empty, and a healthy release was rolled back. No data now counts as *inconclusive*, which pauses the rollout instead of rolling back or promoting without evidence. See D-015 in [DECISIONS.md](DECISIONS.md).
