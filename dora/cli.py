# Written by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Command line entry point: fetch deployments, compute, write json, html and markdown
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .github import GitHub, GitHubError, fetch_deployments, resolve_token
from .metrics import compute
from .render import render_html, render_markdown


def main(argv: list[str] | None = None, client: GitHub | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m dora", description="DORA metrics from GitHub Actions."
    )
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"), help="owner/name")
    parser.add_argument("--days", type=int, default=30, help="window in days (default 30)")
    parser.add_argument("--out", default="build/dora", help="output directory")
    parser.add_argument(
        "--workflow", default="publish.yml", help="workflow file that counts as a deployment"
    )
    parser.add_argument("--branch", default="main")
    args = parser.parse_args(argv)

    if not args.repo:
        print("error: --repo owner/name (or GITHUB_REPOSITORY) is required", file=sys.stderr)
        return 2
    if args.days < 1:
        print("error: --days must be at least 1", file=sys.stderr)
        return 2

    client = client or GitHub(resolve_token())
    try:
        deployments = fetch_deployments(client, args.repo, args.days, args.workflow, args.branch)
    except GitHubError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    report = compute(deployments, args.days)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (out / "index.html").write_text(render_html(report, args.repo), encoding="utf-8")
    summary = render_markdown(report, args.repo)
    (out / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)
    print(f"wrote {out / 'report.json'}, {out / 'index.html'}, {out / 'summary.md'}")
    return 0
