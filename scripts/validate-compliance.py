#!/usr/bin/env python3
# Written by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Solo-developer adaptation of the multi-engineer compliance validator
# Modified by Amukelani (Claude Sonnet 5.5) on 2026-10-25 — Reformatted with ruff to satisfy the project's lint gate
"""Project compliance and repository hygiene validator (solo developer).

Enforces:
1. No direct commits on main/master (skipped in CI and on detached HEAD).
2. Branch naming convention: feature/, bugfix/, fix/, chore/, docs/, hotfix/, release/.
3. WORKLOG.md is updated alongside other changes (warning locally, error with --strict).
4. Git hygiene: no forbidden files tracked (.env, secrets, node_modules, caches).

Usage:
    python scripts/validate-compliance.py                       # local / pre-commit
    python scripts/validate-compliance.py --strict --base origin/main   # CI
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import subprocess
import sys

PROTECTED_BRANCHES = {"main", "master"}
VALID_PREFIXES = ("feature/", "bugfix/", "fix/", "chore/", "docs/", "hotfix/", "release/")

# Matched against every path component and the full path. `.env.example` is allowed.
FORBIDDEN_TRACKED = (
    ".env",
    ".env.*",
    "node_modules",
    "__pycache__",
    ".venv",
    "*.pem",
    "*.key",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
)
ALLOWED_TRACKED = {".env.example"}


def run_git(*args: str) -> str:
    res = subprocess.run(["git", *args], capture_output=True, text=True, check=True)
    return res.stdout.strip()


def in_ci() -> bool:
    return os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true"


def check_branch(errors: list[str]) -> None:
    branch = run_git("branch", "--show-current")
    if in_ci() or not branch:
        print("[*] Branch checks skipped (CI or detached HEAD)")
        return
    print(f"[*] Checking active branch: {branch}")
    if branch in PROTECTED_BRANCHES:
        errors.append(
            f"Direct commits to '{branch}' are prohibited. Create a branch, e.g. feature/<slug>."
        )
    elif not branch.startswith(VALID_PREFIXES):
        errors.append(
            f"Branch '{branch}' does not match the naming convention "
            f"({', '.join(VALID_PREFIXES)}), e.g. feature/P3-docker-image."
        )


def is_forbidden(path: str) -> bool:
    if os.path.basename(path) in ALLOWED_TRACKED:
        return False
    parts = path.split("/")
    return any(fnmatch.fnmatch(part, pat) for part in parts for pat in FORBIDDEN_TRACKED)


def check_hygiene(errors: list[str]) -> None:
    print("[*] Checking tracked files for forbidden paths...")
    for path in run_git("ls-files").splitlines():
        if is_forbidden(path):
            errors.append(f"Forbidden file is tracked in git: '{path}'")


def changed_files(base: str | None) -> list[str]:
    if base:
        out = run_git("diff", "--name-only", f"{base}...HEAD")
    else:
        out = run_git("diff", "--cached", "--name-only")
    return [line for line in out.splitlines() if line]


def check_worklog(base: str | None, strict: bool, errors: list[str]) -> None:
    print("[*] Checking WORKLOG.md status...")
    files = changed_files(base)
    others = [f for f in files if f != "WORKLOG.md"]
    if others and "WORKLOG.md" not in files:
        msg = "WORKLOG.md was not updated alongside the other changes. Append a row before committing."
        if strict:
            errors.append(msg)
        else:
            print(f"[!] NOTICE: {msg}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--strict", action="store_true", help="fail (not warn) when WORKLOG.md is not updated"
    )
    parser.add_argument(
        "--base", help="compare against this ref (e.g. origin/main) instead of staged changes"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Project Compliance Validator")
    print("=" * 60)

    errors: list[str] = []
    try:
        check_branch(errors)
        check_hygiene(errors)
        check_worklog(args.base, args.strict, errors)
    except subprocess.CalledProcessError as exc:
        print(f"[!] git command failed: {exc.cmd} -> {exc.stderr.strip()}")
        sys.exit(2)

    print("=" * 60)
    if errors:
        for err in errors:
            print(f"[!] ERROR: {err}")
        sys.exit(1)
    print("[OK] All automated compliance checks passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
