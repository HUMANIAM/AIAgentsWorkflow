#!/usr/bin/env python3
"""Unit tests for workspace bootstrap helpers."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from orchestrator import workspace_bootstrap as wb


def _seed_runtime(runtime_root: Path) -> None:
    (runtime_root / "rules").mkdir(parents=True, exist_ok=True)
    (runtime_root / "rules" / "env_key_allowlist.txt").write_text(
        "AI_API_KEY\nGOOGLE_SHEETS_SPREADSHEET_ID\nGOOGLE_APPLICATION_CREDENTIALS\n",
        encoding="utf-8",
    )


def _seed_source_env(tmp_path: Path) -> Path:
    creds = tmp_path / "creds.json"
    creds.write_text('{"type":"service_account"}\n', encoding="utf-8")
    source_env = tmp_path / "source.env"
    source_env.write_text(
        "\n".join(
            [
                "AI_API_KEY=test-key",
                "GOOGLE_SHEETS_SPREADSHEET_ID=sheet-id",
                f"GOOGLE_APPLICATION_CREDENTIALS={creds}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return source_env


def test_default_source_env_paths_are_repo_root_based():
    assert wb.PRIMARY_SOURCE_ENV == wb.REPO_ROOT / "agent_runtime" / "steward_ai_zorba_bot" / ".env"
    assert wb.FALLBACK_SOURCE_ENV == wb.REPO_ROOT / "steward_ai_zorba_bot" / ".env"


def test_bootstrap_preserves_existing_role_adapter(tmp_path: Path):
    runtime_root = tmp_path / "runtime"
    _seed_runtime(runtime_root)
    source_env = _seed_source_env(tmp_path)

    workspace = wb.bootstrap_workspace_for_idea(
        runtime_root=runtime_root,
        idea_id="expense_tracker",
        headline="Expense Tracker",
        source_env_file=source_env,
    )
    adapter = workspace / "adapter" / "role_adapter.py"
    original = adapter.read_text(encoding="utf-8")
    marker = "\n# custom-adapter-marker\n"
    adapter.write_text(original + marker, encoding="utf-8")

    wb.bootstrap_workspace_for_idea(
        runtime_root=runtime_root,
        idea_id="expense_tracker",
        headline="Expense Tracker",
        source_env_file=source_env,
    )

    latest = adapter.read_text(encoding="utf-8")
    assert latest.endswith(marker)
