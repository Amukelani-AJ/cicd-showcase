# Written by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Initial FastAPI service: root, health and version routes
import os

from fastapi import FastAPI

SERVICE_NAME = "cicd-showcase"

app = FastAPI(title=SERVICE_NAME)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": SERVICE_NAME, "message": "Hello from the pipeline"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/version")
def version() -> dict[str, str]:
    return {
        "version": os.environ.get("APP_VERSION", "dev"),
        "git_sha": os.environ.get("GIT_SHA", "unknown"),
    }
