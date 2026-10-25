# Written by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — DORA metric calculations as pure functions over a list of deployments
# Modified by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Count lead-time samples skipped for clock skew instead of dropping them silently
"""DORA software delivery metrics, computed from deployments.

Definitions follow https://dora.dev/guides/dora-metrics/ (five metrics, two groups):

  Throughput   change lead time, deployment frequency, failed deployment recovery time
  Instability  change fail rate, deployment rework rate

A "deployment" here is a run of the Publish workflow on main: the point where a merged change becomes a
signed, published image and a new tag in Git. Everything after that (Argo CD sync, canary analysis,
rollback) happens in the cluster, which GitHub cannot see, so the instability metrics are proxies and
the report says so.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import mean, median

# Conventional-commit types that mean "unplanned work to fix something": fix, hotfix, revert.
REWORK_TITLE = re.compile(r"^(?:(?:fix|hotfix|revert)(?:\([^)]*\))?!?:|revert\b)", re.IGNORECASE)


@dataclass(frozen=True)
class Deployment:
    run_id: int
    sha: str
    finished_at: datetime
    succeeded: bool
    pr_number: int | None = None
    pr_title: str | None = None
    first_commit_at: datetime | None = None  # earliest authored commit in the PR


def percentile(values: list[float], pct: float) -> float | None:
    """Nearest-rank percentile; None for an empty list."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


def is_rework(title: str | None) -> bool:
    return bool(title and REWORK_TITLE.match(title.strip()))


def deployment_frequency(deployments: list[Deployment], days: int) -> dict:
    """Successful deployments per day, plus a per-day histogram for the chart."""
    ok = [d for d in deployments if d.succeeded]
    by_day: dict[str, int] = {}
    for d in ok:
        key = d.finished_at.astimezone(UTC).date().isoformat()
        by_day[key] = by_day.get(key, 0) + 1
    return {
        "total": len(ok),
        "per_day": round(len(ok) / days, 2) if days > 0 else None,
        "by_day": dict(sorted(by_day.items())),
    }


def lead_times(deployments: list[Deployment]) -> list[timedelta]:
    """Earliest commit to successful deployment, for deployments that came from a PR."""
    out = []
    for d in deployments:
        if d.succeeded and d.first_commit_at is not None and d.finished_at >= d.first_commit_at:
            out.append(d.finished_at - d.first_commit_at)
    return out


def lead_time_summary(deployments: list[Deployment]) -> dict:
    seconds = [t.total_seconds() for t in lead_times(deployments)]
    # A commit cannot be authored after the deployment it caused. When it looks like it was, the
    # author's clock was ahead of GitHub's; count those instead of dropping them without a trace.
    skipped = sum(
        1
        for d in deployments
        if d.succeeded and d.first_commit_at is not None and d.finished_at < d.first_commit_at
    )
    if not seconds:
        return {
            "count": 0,
            "skipped_clock_skew": skipped,
            "median_s": None,
            "p90_s": None,
            "mean_s": None,
        }
    return {
        "count": len(seconds),
        "skipped_clock_skew": skipped,
        "median_s": median(seconds),
        "p90_s": percentile(seconds, 90),
        "mean_s": mean(seconds),
    }


def change_fail_rate(deployments: list[Deployment]) -> dict:
    """Share of deployments that failed. Proxy: a failed Publish run on main."""
    total = len(deployments)
    failed = sum(1 for d in deployments if not d.succeeded)
    return {"failed": failed, "total": total, "rate": (failed / total) if total else None}


def recovery_times(deployments: list[Deployment]) -> list[timedelta]:
    """For each failed deployment, the time until the next successful one."""
    ordered = sorted(deployments, key=lambda d: d.finished_at)
    out = []
    for i, d in enumerate(ordered):
        if d.succeeded:
            continue
        for later in ordered[i + 1 :]:
            if later.succeeded:
                out.append(later.finished_at - d.finished_at)
                break
    return out


def recovery_summary(deployments: list[Deployment]) -> dict:
    seconds = [t.total_seconds() for t in recovery_times(deployments)]
    if not seconds:
        return {"count": 0, "median_s": None, "max_s": None}
    return {"count": len(seconds), "median_s": median(seconds), "max_s": max(seconds)}


def rework_rate(deployments: list[Deployment]) -> dict:
    """Share of PR-driven deployments that are fixes or reverts (unplanned work). Proxy by PR title."""
    prs = [d for d in deployments if d.succeeded and d.pr_title is not None]
    rework = sum(1 for d in prs if is_rework(d.pr_title))
    return {"rework": rework, "total": len(prs), "rate": (rework / len(prs)) if prs else None}


def compute(deployments: list[Deployment], days: int, now: datetime | None = None) -> dict:
    """The full report as a JSON-serialisable dict."""
    now = now or datetime.now(UTC)
    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "window_days": days,
        "deployments_considered": len(deployments),
        "deployment_frequency": deployment_frequency(deployments, days),
        "lead_time": lead_time_summary(deployments),
        "failed_deployment_recovery": recovery_summary(deployments),
        "change_fail_rate": change_fail_rate(deployments),
        "rework_rate": rework_rate(deployments),
        "deployments": [
            {
                "run_id": d.run_id,
                "sha": d.sha[:7],
                "finished_at": d.finished_at.astimezone(UTC).isoformat(timespec="seconds"),
                "succeeded": d.succeeded,
                "pr": d.pr_number,
                "title": d.pr_title,
            }
            for d in sorted(deployments, key=lambda d: d.finished_at)
        ],
    }
