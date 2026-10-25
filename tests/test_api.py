# Written by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Tests for the root, health and version routes
# Modified by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Added tests for /metrics, request counting and FAIL_RATE failure injection
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app.main import app

client = TestClient(app)


def test_root_identifies_service():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"service": "cicd-showcase", "message": "Hello from the pipeline"}


def test_health_is_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version_defaults_when_env_missing(monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.delenv("GIT_SHA", raising=False)
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == {"version": "dev", "git_sha": "unknown"}


def test_version_reads_build_metadata(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "1.2.3")
    monkeypatch.setenv("GIT_SHA", "abc1234")
    response = client.get("/version")
    assert response.json() == {"version": "1.2.3", "git_sha": "abc1234"}


def test_unknown_route_returns_404():
    assert client.get("/nope").status_code == 404


def _count(path: str, status: str, method: str = "GET") -> float:
    value = REGISTRY.get_sample_value(
        "http_requests_total", {"method": method, "path": path, "status": status}
    )
    return value or 0.0


def test_metrics_endpoint_exposes_prometheus_text():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds_bucket" in response.text


def test_requests_are_counted_by_route_and_status():
    before = _count("/health", "200")
    client.get("/health")
    client.get("/health")
    assert _count("/health", "200") == before + 2


def test_unknown_paths_share_one_label_so_cardinality_stays_bounded():
    before = _count("unmatched", "404")
    client.get("/does-not-exist-1")
    client.get("/does-not-exist-2")
    assert _count("unmatched", "404") == before + 2


def test_metrics_endpoint_does_not_count_itself():
    client.get("/metrics")
    assert _count("/metrics", "200") == 0.0


def test_fail_rate_one_makes_root_fail_and_counts_the_500(monkeypatch):
    monkeypatch.setenv("FAIL_RATE", "1")
    before = _count("/", "500")
    response = client.get("/")
    assert response.status_code == 500
    assert _count("/", "500") == before + 1


def test_fail_rate_zero_and_garbage_values_never_fail(monkeypatch):
    for value in ("0", "not-a-number", "-3"):
        monkeypatch.setenv("FAIL_RATE", value)
        assert client.get("/").status_code == 200


def test_fail_rate_does_not_affect_health(monkeypatch):
    monkeypatch.setenv("FAIL_RATE", "1")
    assert client.get("/health").status_code == 200
