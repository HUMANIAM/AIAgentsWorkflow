#!/usr/bin/env python3
"""Git protocol helpers for realization-mode role execution."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, Optional


COMMIT_RE = re.compile(
    r"^(feat|fix|docs|test|refactor|style|chore|security|review)\((?P<role>[a-z0-9_]+)\): .+"
)


def _git(workspace: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )


def collect_head_sha(workspace: Path) -> str:
    cp = _git(workspace, "rev-parse", "--verify", "HEAD")
    if cp.returncode != 0:
        return ""
    return (cp.stdout or "").strip()


def _last_commit_subject(workspace: Path) -> str:
    cp = _git(workspace, "log", "-1", "--pretty=%s")
    if cp.returncode != 0:
        return ""
    return (cp.stdout or "").strip()


def validate_step_commit(workspace: Path, pre_sha: str, role: str) -> Optional[str]:
    post_sha = collect_head_sha(workspace)
    if not post_sha or post_sha == pre_sha:
        return "Git protocol violation: role step produced no new commit."

    subject = _last_commit_subject(workspace)
    match = COMMIT_RE.match(subject)
    if not match:
        return (
            "Git protocol violation: commit message must match "
            "`<type>(<role>): <intent>`."
        )
    if match.group("role") != role:
        return (
            f"Git protocol violation: commit role scope `{match.group('role')}` "
            f"does not match current role `{role}`."
        )
    return None


def write_commit_ledger(
    status: Dict[str, Any],
    artifacts_dir: Path,
    *,
    now_fn: Callable[[], str],
) -> None:
    entries = status.get("commit_evidence", [])
    if not isinstance(entries, list) or not entries:
        return

    lines = [
        "# Commit Ledger",
        "",
        "| Timestamp | Role | Step | Commit | Message |",
        "|---|---|---|---|---|",
    ]
    for item in entries:
        if not isinstance(item, dict):
            continue
        lines.append(
            "| {created_at} | {role} | {step_id} | `{commit_sha}` | {message} |".format(
                created_at=item.get("created_at", ""),
                role=item.get("role", ""),
                step_id=item.get("step_id", ""),
                commit_sha=item.get("commit_sha", ""),
                message=str(item.get("message", "")).replace("|", "\\|"),
            )
        )

    ledger = artifacts_dir / "10_commit_ledger.md"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")
    status.setdefault("artifacts", {})["10_commit_ledger.md"] = {
        "path": str(ledger),
        "owner": "orchestrator",
        "updated_at": now_fn(),
    }
