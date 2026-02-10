#!/usr/bin/env python3
"""Unit tests for orchestrator git protocol helpers."""

from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from orchestrator import git_protocol


def _git(path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=path,
        capture_output=True,
        text=True,
        check=False,
    )


def _seed_repo(path: Path) -> None:
    _git(path, "init")
    _git(path, "config", "user.name", "Test User")
    _git(path, "config", "user.email", "test@example.com")
    (path / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(path, "add", ".")
    _git(path, "commit", "-m", "chore(orchestrator): bootstrap")


def test_validate_step_commit_passes_for_matching_role(tmp_path: Path):
    _seed_repo(tmp_path)
    pre_sha = git_protocol.collect_head_sha(tmp_path)

    (tmp_path / "change.txt").write_text("change\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "feat(system_analyst): add acceptance criteria draft")

    violation = git_protocol.validate_step_commit(tmp_path, pre_sha, "system_analyst")
    assert violation is None


def test_validate_step_commit_rejects_role_scope_mismatch(tmp_path: Path):
    _seed_repo(tmp_path)
    pre_sha = git_protocol.collect_head_sha(tmp_path)

    (tmp_path / "change.txt").write_text("change\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "feat(backend_engineer): implement handler")

    violation = git_protocol.validate_step_commit(tmp_path, pre_sha, "frontend_engineer")
    assert violation is not None
    assert "does not match current role" in violation


def test_write_commit_ledger_creates_artifact(tmp_path: Path):
    status = {
        "commit_evidence": [
            {
                "step_id": "requirements_owner",
                "role": "system_analyst",
                "commit_sha": "abc123",
                "message": "feat(system_analyst): write acceptance contract",
                "created_at": "2026-02-08T00:00:00Z",
            }
        ]
    }
    artifacts_dir = tmp_path / "artifacts"
    git_protocol.write_commit_ledger(status, artifacts_dir, now_fn=lambda: "2026-02-08T00:00:01Z")

    ledger = artifacts_dir / "10_commit_ledger.md"
    assert ledger.exists()
    body = ledger.read_text(encoding="utf-8")
    assert "feat(system_analyst): write acceptance contract" in body
    assert "10_commit_ledger.md" in status["artifacts"]
