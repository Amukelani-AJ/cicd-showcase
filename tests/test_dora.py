# Written by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Tests for the DORA package: metric math, GitHub client, rendering and the CLI
import io
import json
import subprocess
import urllib.error
from datetime import UTC, datetime, timedelta

import pytest

from dora import cli, github, metrics, render
from dora.metrics import Deployment


def t(hour: int, minute: int = 0, day: int = 25) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=UTC)


def dep(run_id, finished, ok=True, pr=None, title=None, first_commit=None, sha="abcdef1234567"):
    return Deployment(run_id, sha, finished, ok, pr, title, first_commit)


# ---------------------------------------------------------------- metrics


def test_percentile_uses_nearest_rank():
    assert metrics.percentile([], 90) is None
    assert metrics.percentile([1, 2, 3], 50) == 2
    assert metrics.percentile(list(range(1, 11)), 90) == 9
    assert metrics.percentile([5], 99) == 5


@pytest.mark.parametrize(
    "title",
    [
        "fix: crash",
        "fix(api): crash",
        "hotfix: now",
        "Revert: x",
        'Revert "feat: x"',
        "fix!: break",
    ],
)
def test_rework_titles_are_recognised(title):
    assert metrics.is_rework(title)


@pytest.mark.parametrize(
    "title",
    ["feat: add a fix", "fixture: data", "reverted: no", "docs: x", "", None, "chore: revert-ish"],
)
def test_planned_work_is_not_rework(title):
    assert not metrics.is_rework(title)


def test_deployment_frequency_counts_only_successes_by_utc_day():
    deploys = [
        dep(1, t(9)),
        dep(2, t(23, 59)),
        dep(3, t(0, 5, day=26)),
        dep(4, t(10), ok=False),
    ]
    freq = metrics.deployment_frequency(deploys, days=10)
    assert freq["total"] == 3
    assert freq["per_day"] == 0.3
    assert freq["by_day"] == {"2026-10-25": 2, "2026-10-26": 1}


def test_deployment_frequency_handles_a_zero_day_window():
    assert metrics.deployment_frequency([dep(1, t(9))], days=0)["per_day"] is None


def test_lead_time_is_first_commit_to_deployment_for_successful_prs():
    deploys = [
        dep(1, t(10), first_commit=t(9)),  # 1h
        dep(2, t(12), first_commit=t(11, 30)),  # 30m
        dep(3, t(13), first_commit=None),  # direct push: no lead time
        dep(4, t(14), ok=False, first_commit=t(8)),  # failed: not counted
    ]
    assert metrics.lead_times(deploys) == [timedelta(hours=1), timedelta(minutes=30)]
    summary = metrics.lead_time_summary(deploys)
    assert summary["count"] == 2
    assert summary["median_s"] == 2700
    assert summary["p90_s"] == 3600
    assert summary["mean_s"] == 2700
    assert summary["skipped_clock_skew"] == 0


def test_lead_time_counts_commits_dated_after_their_deployment():
    skewed = dep(1, t(10), first_commit=t(10, 2))  # author clock ahead of GitHub's
    fine = dep(2, t(12), first_commit=t(11))
    summary = metrics.lead_time_summary([skewed, fine])
    assert summary["count"] == 1
    assert summary["skipped_clock_skew"] == 1


def test_lead_time_summary_with_nothing_to_measure():
    summary = metrics.lead_time_summary([dep(1, t(10))])
    assert summary == {
        "count": 0,
        "skipped_clock_skew": 0,
        "median_s": None,
        "p90_s": None,
        "mean_s": None,
    }
    only_skewed = metrics.lead_time_summary([dep(1, t(10), first_commit=t(11))])
    assert only_skewed["count"] == 0 and only_skewed["skipped_clock_skew"] == 1


def test_change_fail_rate():
    assert metrics.change_fail_rate([]) == {"failed": 0, "total": 0, "rate": None}
    deploys = [dep(1, t(9)), dep(2, t(10), ok=False), dep(3, t(11)), dep(4, t(12), ok=False)]
    assert metrics.change_fail_rate(deploys) == {"failed": 2, "total": 4, "rate": 0.5}


def test_recovery_time_is_failure_to_next_success():
    deploys = [
        dep(4, t(12)),  # out of order on purpose
        dep(1, t(9), ok=False),
        dep(2, t(10), ok=False),  # second failure in a row recovers at the same deployment
        dep(5, t(15), ok=False),  # never recovered inside the window
    ]
    assert metrics.recovery_times(deploys) == [timedelta(hours=3), timedelta(hours=2)]
    summary = metrics.recovery_summary(deploys)
    assert summary == {"count": 2, "median_s": 9000, "max_s": 10800}


def test_recovery_summary_when_nothing_failed():
    assert metrics.recovery_summary([dep(1, t(9))]) == {"count": 0, "median_s": None, "max_s": None}


def test_rework_rate_counts_only_successful_pr_deployments():
    deploys = [
        dep(1, t(9), pr=1, title="feat: a"),
        dep(2, t(10), pr=2, title="fix: b"),
        dep(3, t(11), pr=3, title='Revert "feat: a"'),
        dep(4, t(12), pr=4, title="fix: c", ok=False),  # failed run: not counted
        dep(5, t(13)),  # direct push: no PR title
    ]
    assert metrics.rework_rate(deploys) == {"rework": 2, "total": 3, "rate": pytest.approx(2 / 3)}
    assert metrics.rework_rate([]) == {"rework": 0, "total": 0, "rate": None}


def test_compute_assembles_a_serialisable_report():
    deploys = [
        dep(2, t(11), pr=2, title="fix: x", first_commit=t(10)),
        dep(1, t(9), sha="1234567890ab"),
    ]
    report = metrics.compute(deploys, days=7, now=t(12))
    json.dumps(report)  # must be JSON-serialisable
    assert report["generated_at"] == "2026-10-25T12:00:00+00:00"
    assert report["window_days"] == 7
    assert report["deployments_considered"] == 2
    assert [d["run_id"] for d in report["deployments"]] == [1, 2]  # sorted by time
    assert report["deployments"][0]["sha"] == "1234567"
    assert report["rework_rate"]["rework"] == 1
    assert metrics.compute([], days=1)["generated_at"]  # default clock


# ---------------------------------------------------------------- github client


class FakeResponse(io.BytesIO):
    pass


class FakeOpener:
    """Stands in for urllib.request.urlopen and records every request."""

    def __init__(self, *payloads):
        self.payloads = list(payloads)
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        payload = self.payloads.pop(0) if len(self.payloads) > 1 else self.payloads[0]
        if isinstance(payload, Exception):
            raise payload
        return FakeResponse(json.dumps(payload).encode())


def test_get_sends_auth_headers_and_query_string():
    opener = FakeOpener({"ok": True})
    client = github.GitHub("tok", opener=opener)
    assert client.get("/repos/x/y", {"a": 1}) == {"ok": True}
    request = opener.requests[0]
    assert request.full_url == "https://api.github.com/repos/x/y?a=1"
    assert request.get_header("Authorization") == "Bearer tok"
    assert request.get_header("X-github-api-version") == "2022-11-28"


def test_get_without_a_token_sends_no_authorization():
    opener = FakeOpener([])
    github.GitHub(None, opener=opener).get("/x")
    assert opener.requests[0].get_header("Authorization") is None


def test_http_errors_become_github_errors_with_a_rate_limit_hint():
    limited = urllib.error.HTTPError("u", 403, "forbidden", {}, None)
    with pytest.raises(github.GitHubError, match="rate limited"):
        github.GitHub("t", opener=FakeOpener(limited)).get("/x")
    missing = urllib.error.HTTPError("u", 404, "nf", {}, None)
    with pytest.raises(github.GitHubError) as info:
        github.GitHub("t", opener=FakeOpener(missing)).get("/x")
    assert "HTTP 404" in str(info.value) and "rate limited" not in str(info.value)


def test_network_errors_become_github_errors():
    down = urllib.error.URLError("no route")
    with pytest.raises(github.GitHubError, match="no route"):
        github.GitHub("t", opener=FakeOpener(down)).get("/x")


def test_paginate_follows_pages_until_a_short_one():
    page1 = {"items": list(range(100))}
    page2 = {"items": [100, 101, 102]}
    opener = FakeOpener(page1, page2)
    got = github.GitHub("t", opener=opener).paginate("/p", key="items")
    assert got == list(range(103))
    assert len(opener.requests) == 2
    assert "page=2" in opener.requests[1].full_url


def test_paginate_without_a_key_and_with_a_single_short_page():
    opener = FakeOpener([1, 2, 3])
    assert github.GitHub("t", opener=opener).paginate("/p") == [1, 2, 3]
    assert len(opener.requests) == 1


def test_paginate_has_a_hard_page_limit():
    opener = FakeOpener(list(range(100)))  # every page is full, forever
    got = github.GitHub("t", opener=opener).paginate("/p")
    assert len(opener.requests) == github.MAX_PAGES
    assert len(got) == 100 * github.MAX_PAGES


def test_token_resolution_order(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "from-env")
    assert github.resolve_token() == "from-env"
    monkeypatch.delenv("GITHUB_TOKEN")
    monkeypatch.setenv("GH_TOKEN", "from-gh-env")
    assert github.resolve_token() == "from-gh-env"

    monkeypatch.delenv("GH_TOKEN")

    def fake_run(returncode, stdout):
        return lambda *a, **k: subprocess.CompletedProcess(a, returncode, stdout, "")

    monkeypatch.setattr(github.subprocess, "run", fake_run(0, "from-cli\n"))
    assert github.resolve_token() == "from-cli"
    monkeypatch.setattr(github.subprocess, "run", fake_run(0, "\n"))
    assert github.resolve_token() is None
    monkeypatch.setattr(github.subprocess, "run", fake_run(1, "ignored"))
    assert github.resolve_token() is None

    def missing(*a, **k):
        raise FileNotFoundError("gh")

    monkeypatch.setattr(github.subprocess, "run", missing)
    assert github.resolve_token() is None


def test_parse_time_understands_zulu():
    assert github.parse_time("2026-10-25T10:00:00Z") == t(10)


class FakeClient:
    def __init__(self, runs, pulls, commits):
        self.runs, self.pulls, self.commits = runs, pulls, commits
        self.calls = []

    def paginate(self, path, params=None, key=None):
        self.calls.append(path)
        if key == "workflow_runs":
            return self.runs
        number = path.split("/")[-2]
        return self.commits.get(number, [])

    def get(self, path, params=None):
        self.calls.append(path)
        return self.pulls.get(path.split("/")[-2], [])


def run(run_id, sha, conclusion, updated="2026-10-25T10:30:00Z"):
    return {"id": run_id, "head_sha": sha, "conclusion": conclusion, "updated_at": updated}


def test_fetch_deployments_enriches_runs_with_their_pull_requests():
    client = FakeClient(
        runs=[
            run(1, "aaa", "success"),
            run(2, "bbb", "failure"),
            run(3, "ccc", "cancelled"),  # not a deployment
            run(4, "ddd", "success"),  # direct push, no PR
            run(5, "eee", "success"),  # PR without readable commits
        ],
        pulls={
            "aaa": [
                {"number": 9, "title": "other", "merge_commit_sha": "zzz"},
                {"number": 7, "title": "feat: it", "merge_commit_sha": "aaa"},
            ],
            "bbb": [{"number": 8, "title": "fix: it", "merge_commit_sha": "other"}],
            "eee": [{"number": 10, "title": "docs: it", "merge_commit_sha": "eee"}],
        },
        commits={
            "7": [
                {"commit": {"author": {"date": "2026-10-25T10:10:00Z"}}},
                {"commit": {"author": {"date": "2026-10-25T09:50:00Z"}}},
            ],
            "8": [{"commit": {"author": {"date": "2026-10-25T10:00:00Z"}}}],
        },
    )
    out = github.fetch_deployments(client, "o/r", days=30, now=t(12))
    assert [d.run_id for d in out] == [1, 2, 4, 5]
    first = out[0]
    assert (first.pr_number, first.pr_title, first.succeeded) == (
        7,
        "feat: it",
        True,
    )  # merge sha wins
    assert first.first_commit_at == t(9, 50)
    assert out[1].succeeded is False and out[1].pr_number == 8  # falls back to the first PR
    assert out[2].pr_number is None and out[2].first_commit_at is None
    assert out[3].pr_number == 10 and out[3].first_commit_at is None
    assert out[0].finished_at == t(10, 30)


def test_fetch_deployments_asks_only_for_the_window_and_branch():
    seen = {}

    class Spy(FakeClient):
        def paginate(self, path, params=None, key=None):
            seen.update(path=path, params=params)
            return []

    github.fetch_deployments(
        Spy([], {}, {}), "o/r", days=7, workflow="x.yml", branch="trunk", now=t(12)
    )
    assert seen["path"] == "/repos/o/r/actions/workflows/x.yml/runs"
    assert seen["params"]["branch"] == "trunk"
    assert seen["params"]["created"] == ">=2026-10-18T12:00:00Z"


# ---------------------------------------------------------------- rendering


def sample_report(**overrides):
    deploys = [
        dep(1, t(9), pr=1, title="feat: a", first_commit=t(8, 40)),
        dep(2, t(10), ok=False, pr=2, title="fix: b"),
        dep(3, t(11), pr=3, title="fix: b again", first_commit=t(10, 50)),
    ]
    report = metrics.compute(deploys, days=30, now=t(12))
    report.update(overrides)
    return report


def test_durations_and_rates_are_human_readable():
    assert render.fmt_duration(None) == "n/a"
    assert render.fmt_duration(5) == "5s"
    assert render.fmt_duration(75) == "1m 15s"
    assert render.fmt_duration(3700) == "1h 01m"
    assert render.fmt_duration(90000) == "1d 1h"
    assert render.fmt_rate(None) == "n/a"
    assert render.fmt_rate(0.5) == "50%"


def test_rows_cover_all_five_dora_metrics():
    names = [name for _, name, _, _ in render.rows(sample_report())]
    assert names == [
        "Deployment frequency",
        "Change lead time",
        "Failed deployment recovery time",
        "Change fail rate",
        "Deployment rework rate",
    ]


def test_rows_with_no_data_say_n_a():
    empty = metrics.compute([], days=30, now=t(12))
    values = {name: value for _, name, value, _ in render.rows(empty)}
    assert values["Deployment frequency"] == "0.0/day"
    assert values["Change lead time"] == "n/a"
    assert values["Change fail rate"] == "n/a"
    freq_none = sample_report()
    freq_none["deployment_frequency"]["per_day"] = None
    assert render.rows(freq_none)[0][2] == "n/a"


def test_markdown_has_a_table_and_the_proxy_note():
    text = render.render_markdown(sample_report(), "o/r")
    assert "## DORA metrics for o/r" in text
    assert "| Throughput | Deployment frequency |" in text
    assert "proxies" in text


def test_skipped_lead_time_samples_are_called_out():
    report = sample_report()
    report["lead_time"]["skipped_clock_skew"] = 2
    assert "2 skipped" in render.render_markdown(report, "o/r")


def test_html_escapes_untrusted_titles():
    evil = '<script>alert("x")</script>'
    deploys = [dep(1, t(9), pr=1, title=evil, first_commit=t(8))]
    html = render.render_html(metrics.compute(deploys, days=30, now=t(12)), "o/<r>")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "o/&lt;r&gt;" in html


def test_html_is_self_contained_and_has_a_chart():
    html = render.render_html(sample_report(), "o/r")
    assert html.startswith("<!doctype html>")
    assert "<svg" in html and "Deployments per day" in html
    assert "http://" not in html and "https://" not in html
    assert "<script" not in html


def test_html_handles_a_window_with_no_deployments():
    html = render.render_html(metrics.compute([], days=30, now=t(12)), "o/r")
    assert "No deployments in this window." in html
    assert "None in this window." in html


def test_html_marks_failed_deployments_and_direct_pushes():
    html = render.render_html(
        metrics.compute([dep(1, t(9), ok=False), dep(2, t(10))], days=30, now=t(12)), "o/r"
    )
    assert 'class="failed">failed' in html
    assert "direct push" in html


# ---------------------------------------------------------------- cli


def test_cli_writes_json_html_and_markdown(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        cli, "fetch_deployments", lambda *a, **k: [dep(1, t(9), pr=1, title="feat: a")]
    )
    code = cli.main(["--repo", "o/r", "--days", "7", "--out", str(tmp_path)], client=object())
    assert code == 0
    assert json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))["window_days"] == 7
    assert "<!doctype html>" in (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "DORA metrics for o/r" in (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert "wrote" in capsys.readouterr().out


def test_cli_builds_its_own_client_when_none_is_given(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "resolve_token", lambda: "tok")
    monkeypatch.setattr(cli, "fetch_deployments", lambda client, *a, **k: [])
    assert cli.main(["--repo", "o/r", "--out", str(tmp_path)]) == 0


def test_cli_reads_the_repo_from_the_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "env/repo")
    monkeypatch.setattr(
        cli, "fetch_deployments", lambda client, repo, *a, **k: [] if repo == "env/repo" else 1 / 0
    )
    assert cli.main(["--out", str(tmp_path)], client=object()) == 0


def test_cli_rejects_missing_repo_and_bad_window(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    assert cli.main(["--out", str(tmp_path)], client=object()) == 2
    assert "required" in capsys.readouterr().err
    assert cli.main(["--repo", "o/r", "--days", "0", "--out", str(tmp_path)], client=object()) == 2
    assert "at least 1" in capsys.readouterr().err


def test_cli_reports_github_failures(tmp_path, monkeypatch, capsys):
    def boom(*a, **k):
        raise github.GitHubError("GET /x failed: HTTP 500")

    monkeypatch.setattr(cli, "fetch_deployments", boom)
    assert cli.main(["--repo", "o/r", "--out", str(tmp_path)], client=object()) == 1
    assert "HTTP 500" in capsys.readouterr().err
