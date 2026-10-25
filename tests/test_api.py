# Written by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Tests for the root, health and version routes
from fastapi.testclient import TestClient

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
