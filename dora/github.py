# Written by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Minimal GitHub REST client and the deployment collector for the DORA report
"""Reads Publish workflow runs and their pull requests from the GitHub REST API (standard library only)."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from .metrics import Deployment

API = "https://api.github.com"
PER_PAGE = 100
MAX_PAGES = 20  # hard stop so a bug can never loop forever (2000 items)


class GitHubError(RuntimeError):
    pass


def resolve_token() -> str | None:
    """GITHUB_TOKEN in CI; locally fall back to the gh CLI's active account."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None if out.returncode == 0 else None


class GitHub:
    def __init__(
        self, token: str | None, opener: Callable = urllib.request.urlopen, api: str = API
    ):
        self.token = token
        self.opener = opener
        self.api = api

    def get(self, path: str, params: dict | None = None):
        url = self.api + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "cicd-showcase-dora",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, headers=headers)
        try:
            with self.opener(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            hint = " (rate limited? set GITHUB_TOKEN)" if exc.code in (403, 429) else ""
            raise GitHubError(f"GET {path} failed: HTTP {exc.code}{hint}") from exc
        except urllib.error.URLError as exc:
            raise GitHubError(f"GET {path} failed: {exc.reason}") from exc

    def paginate(self, path: str, params: dict | None = None, key: str | None = None) -> list:
        items: list = []
        for page in range(1, MAX_PAGES + 1):
            data = self.get(path, {**(params or {}), "per_page": PER_PAGE, "page": page})
            batch = data[key] if key else data
            items.extend(batch)
            if len(batch) < PER_PAGE:
                break
        return items


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def fetch_deployments(
    client: GitHub,
    repo: str,
    days: int,
    workflow: str = "publish.yml",
    branch: str = "main",
    now: datetime | None = None,
) -> list[Deployment]:
    """Completed Publish runs on main within the window, each enriched with its PR when it has one."""
    now = now or datetime.now(UTC)
    since = (now - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    runs = client.paginate(
        f"/repos/{repo}/actions/workflows/{workflow}/runs",
        {"branch": branch, "status": "completed", "created": f">={since}"},
        key="workflow_runs",
    )
    deployments = []
    for run in runs:
        if run.get("conclusion") not in ("success", "failure"):
            continue  # cancelled or skipped runs are not deployments
        pr_number = pr_title = first_commit_at = None
        pulls = client.get(f"/repos/{repo}/commits/{run['head_sha']}/pulls")
        if pulls:
            pr = next((p for p in pulls if p.get("merge_commit_sha") == run["head_sha"]), pulls[0])
            pr_number, pr_title = pr["number"], pr["title"]
            commits = client.paginate(f"/repos/{repo}/pulls/{pr_number}/commits")
            dates = [parse_time(c["commit"]["author"]["date"]) for c in commits]
            first_commit_at = min(dates) if dates else None
        deployments.append(
            Deployment(
                run_id=run["id"],
                sha=run["head_sha"],
                finished_at=parse_time(run["updated_at"]),
                succeeded=run["conclusion"] == "success",
                pr_number=pr_number,
                pr_title=pr_title,
                first_commit_at=first_commit_at,
            )
        )
    return deployments
