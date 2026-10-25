# Written by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Render the DORA report as markdown and as a self-contained HTML dashboard
# Modified by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Show how many lead-time samples were skipped for clock skew
# Modified by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Cap the bar width so a single day of data does not fill the chart
"""Turns the report dict from `metrics.compute` into markdown and static HTML.

The HTML has no external requests (inline CSS and SVG, no scripts) so it can be opened from disk or
hosted anywhere. Every dynamic string is escaped: PR titles are untrusted input.
"""

from __future__ import annotations

from html import escape

NOTE_PROXIES = (
    "A deployment is a run of the Publish workflow on main. Argo CD syncs and Argo Rollouts canary "
    "rollbacks happen in the cluster, which GitHub cannot see, so the two instability metrics are "
    "proxies: change fail rate counts failed Publish runs, and rework rate counts deployed PRs titled "
    "fix, hotfix or revert."
)


def fmt_duration(seconds: float | None) -> str:
    if seconds is None:
        return "n/a"
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {sec:02d}s"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {minutes:02d}m"
    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h"


def fmt_rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.0f}%"


def rows(report: dict) -> list[tuple[str, str, str, str]]:
    """(group, metric, value, detail) for the five DORA metrics."""
    freq = report["deployment_frequency"]
    lead = report["lead_time"]
    rec = report["failed_deployment_recovery"]
    cfr = report["change_fail_rate"]
    rew = report["rework_rate"]
    return [
        (
            "Throughput",
            "Deployment frequency",
            f"{freq['per_day']}/day" if freq["per_day"] is not None else "n/a",
            f"{freq['total']} successful deployments in {report['window_days']} days",
        ),
        (
            "Throughput",
            "Change lead time",
            fmt_duration(lead["median_s"]),
            f"median, first commit to deployment; p90 {fmt_duration(lead['p90_s'])}, n={lead['count']}"
            + (
                f", {lead['skipped_clock_skew']} skipped (commit dated after its deployment: author clock ahead)"
                if lead.get("skipped_clock_skew")
                else ""
            ),
        ),
        (
            "Throughput",
            "Failed deployment recovery time",
            fmt_duration(rec["median_s"]),
            f"median time to the next good deployment; n={rec['count']}",
        ),
        (
            "Instability",
            "Change fail rate",
            fmt_rate(cfr["rate"]),
            f"{cfr['failed']} failed of {cfr['total']} deployments",
        ),
        (
            "Instability",
            "Deployment rework rate",
            fmt_rate(rew["rate"]),
            f"{rew['rework']} fix or revert PRs of {rew['total']} PR deployments",
        ),
    ]


def render_markdown(report: dict, repo: str) -> str:
    lines = [
        f"## DORA metrics for {repo}",
        "",
        f"Last {report['window_days']} days, generated {report['generated_at']}.",
        "",
        "| Group | Metric | Value | Detail |",
        "|---|---|---|---|",
    ]
    for group, metric, value, detail in rows(report):
        lines.append(f"| {group} | {metric} | {value} | {detail} |")
    lines += ["", f"_{NOTE_PROXIES}_", ""]
    return "\n".join(lines)


def _bars(by_day: dict[str, int]) -> str:
    if not by_day:
        return '<p class="muted">No deployments in this window.</p>'
    peak = max(by_day.values())
    width, height, pad = 640, 140, 24
    slot = (width - 2 * pad) / len(by_day)
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Deployments per day" '
        'preserveAspectRatio="xMidYMid meet">'
    ]
    bar_w = min(slot * 0.7, 56)  # keep a lone bar from filling the whole chart
    for i, (day, count) in enumerate(by_day.items()):
        bar_h = (height - 2 * pad) * count / peak
        x = pad + i * slot + (slot - bar_w) / 2
        y = height - pad - bar_h
        mid = x + bar_w / 2
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" '
            f'rx="2" class="bar"><title>{escape(day)}: {count}</title></rect>'
        )
        parts.append(
            f'<text x="{mid:.1f}" y="{y - 4:.1f}" text-anchor="middle" class="val">{count}</text>'
        )
        parts.append(
            f'<text x="{mid:.1f}" y="{height - 8}" text-anchor="middle" '
            f'class="lbl">{escape(day[5:])}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def render_html(report: dict, repo: str) -> str:
    cards = []
    for group, metric, value, detail in rows(report):
        cards.append(
            f'<section class="card"><p class="group">{escape(group)}</p>'
            f'<h2>{escape(metric)}</h2><p class="value">{escape(value)}</p>'
            f'<p class="muted">{escape(detail)}</p></section>'
        )
    deploys = []
    for d in reversed(report["deployments"][-15:]):
        status = "success" if d["succeeded"] else "failed"
        pr = f"#{d['pr']}" if d["pr"] else "direct push"
        deploys.append(
            f"<tr><td>{escape(d['finished_at'].replace('T', ' ').replace('+00:00', ' UTC'))}</td>"
            f"<td><code>{escape(d['sha'])}</code></td><td>{escape(pr)}</td>"
            f'<td>{escape(d["title"] or "")}</td><td class="{status}">{status}</td></tr>'
        )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DORA metrics: {escape(repo)}</title>
<style>
:root {{ --bg:#f6f7f9; --card:#fff; --ink:#15181d; --muted:#5b6472; --line:#dfe3e8; --accent:#2563eb; --ok:#15803d; --bad:#b91c1c; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#0f1318; --card:#171c23; --ink:#e8ebef; --muted:#9aa4b2; --line:#2a313b; --accent:#6ea0ff; --ok:#4ade80; --bad:#f87171; }}
}}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:16px/1.5 system-ui, sans-serif; }}
main {{ max-width: 960px; margin: 0 auto; padding: 24px 16px 48px; }}
h1 {{ font-size: 1.5rem; margin: 0 0 4px; }}
.muted {{ color: var(--muted); font-size: .9rem; margin: 4px 0 0; }}
.grid {{ display:grid; gap:12px; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); margin: 20px 0; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }}
.card h2 {{ font-size: .95rem; margin: 2px 0 6px; font-weight: 600; }}
.group {{ margin:0; font-size:.75rem; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); }}
.value {{ margin:0; font-size:1.9rem; font-weight:700; }}
.panel {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 16px; margin: 12px 0; overflow-x:auto; }}
.panel h2 {{ font-size:1rem; margin:0 0 8px; }}
svg {{ width:100%; height:auto; }}
.bar {{ fill: var(--accent); }} .val {{ fill: var(--ink); font-size: 11px; }} .lbl {{ fill: var(--muted); font-size: 10px; }}
table {{ width:100%; border-collapse:collapse; font-size:.9rem; }}
th, td {{ text-align:left; padding:6px 8px; border-bottom:1px solid var(--line); white-space:nowrap; }}
td:nth-child(4) {{ white-space: normal; }}
.success {{ color: var(--ok); font-weight:600; }} .failed {{ color: var(--bad); font-weight:600; }}
code {{ font-family: ui-monospace, monospace; }}
</style>
</head>
<body>
<main>
<h1>DORA metrics</h1>
<p class="muted">{escape(repo)} &middot; last {report["window_days"]} days &middot; generated {escape(report["generated_at"])}</p>
<div class="grid">
{"".join(cards)}
</div>
<div class="panel"><h2>Deployments per day</h2>{_bars(report["deployment_frequency"]["by_day"])}</div>
<div class="panel"><h2>Recent deployments</h2>
<table><thead><tr><th>Finished</th><th>Commit</th><th>Change</th><th>Title</th><th>Result</th></tr></thead>
<tbody>{"".join(deploys) or '<tr><td colspan="5">None in this window.</td></tr>'}</tbody></table></div>
<div class="panel"><h2>How these are measured</h2><p class="muted">{escape(NOTE_PROXIES)}</p></div>
</main>
</body>
</html>
"""
