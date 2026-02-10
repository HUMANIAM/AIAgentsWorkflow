#!/usr/bin/env python3
"""Workspace bootstrap helpers for realization-mode orchestration."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Dict, List

from orchestrator import utils as orch_utils


VERSION2_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = VERSION2_ROOT.parent
PRIMARY_SOURCE_ENV = REPO_ROOT / "agent_runtime" / "steward_ai_zorba_bot" / ".env"
FALLBACK_SOURCE_ENV = REPO_ROOT / "steward_ai_zorba_bot" / ".env"
DEFAULT_SOURCE_ENV = PRIMARY_SOURCE_ENV if PRIMARY_SOURCE_ENV.exists() else FALLBACK_SOURCE_ENV


class WorkspaceBootstrapError(RuntimeError):
    """Workspace bootstrap failed."""


def _parse_env_file(path: Path) -> Dict[str, str]:
    if not path.exists():
        raise WorkspaceBootstrapError(f"Source env file not found: {path}")

    out: Dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def _load_allowlist(path: Path) -> List[str]:
    if not path.exists():
        raise WorkspaceBootstrapError(f"Allowlist file not found: {path}")
    keys: List[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        keys.append(line)
    return keys


def _git(workspace: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )


def _ensure_git_initialized(workspace: Path, idea_id: str) -> None:
    if not (workspace / ".git").exists():
        init = _git(workspace, "init")
        if init.returncode != 0:
            raise WorkspaceBootstrapError(f"git init failed: {(init.stderr or init.stdout).strip()}")

    _git(workspace, "config", "user.name", "Orchestrator Agent")
    _git(workspace, "config", "user.email", "orchestrator@local")

    head = _git(workspace, "rev-parse", "--verify", "HEAD")
    if head.returncode == 0:
        return

    add = _git(workspace, "add", ".")
    if add.returncode != 0:
        raise WorkspaceBootstrapError(f"git add failed: {(add.stderr or add.stdout).strip()}")

    commit = _git(workspace, "commit", "-m", f"chore(orchestrator): bootstrap workspace for {idea_id}")
    if commit.returncode != 0:
        raise WorkspaceBootstrapError(f"git bootstrap commit failed: {(commit.stderr or commit.stdout).strip()}")


def _write_gitignore(workspace: Path) -> None:
    path = workspace / ".gitignore"
    required = [
        ".env",
        "secrets/*",
        "*.pyc",
        "__pycache__/",
        ".pytest_cache/",
        "node_modules/",
        "playwright-report/",
        "test-results/",
    ]
    lines = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()

    existing = set(lines)
    for item in required:
        if item not in existing:
            lines.append(item)
            existing.add(item)

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_workspace_readme(workspace: Path, idea_id: str, headline: str) -> None:
    path = workspace / "README.md"
    if path.exists():
        return
    path.write_text(
        "\n".join(
            [
                f"# {headline or idea_id}",
                "",
                "Realization workspace created by Version2 orchestrator.",
                "",
                "## Structure",
                "- adapter/: idea-local step executor used by orchestrator",
                "- backend/: API and domain logic",
                "- extension/: browser extension surface",
                "- tests/e2e/: end-to-end automation",
                "- docs/: role outputs and decisions",
                "- artifacts/: execution artifacts",
                "- secrets/: local credentials (gitignored)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_role_adapter(workspace: Path) -> None:
    adapter = workspace / "adapter" / "role_adapter.py"
    adapter.parent.mkdir(parents=True, exist_ok=True)
    if adapter.exists():
        return
    adapter.write_text(
        '''#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _append(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def _workspace() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_env(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    env_file = path / ".env"
    if not env_file.exists():
        return out
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def _seed_backend(workspace: Path) -> None:
    backend = workspace / "backend"
    tests = backend / "tests"
    backend.mkdir(parents=True, exist_ok=True)
    tests.mkdir(parents=True, exist_ok=True)
    (backend / "__init__.py").write_text("", encoding="utf-8")
    (backend / "app.py").write_text(
        "\\n".join(
            [
                "from datetime import datetime, timezone",
                "",
                "def utc_now():",
                "    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')",
                "",
                "def ingest_selection(text: str) -> dict:",
                "    return {'ok': True, 'text': text.strip(), 'created_at': utc_now()}",
            ]
        )
        + "\\n",
        encoding="utf-8",
    )
    (tests / "test_smoke.py").write_text(
        "\\n".join(
            [
                "from backend.app import ingest_selection",
                "",
                "def test_ingest_selection_smoke():",
                "    out = ingest_selection('hello')",
                "    assert out['ok'] is True",
                "    assert out['text'] == 'hello'",
            ]
        )
        + "\\n",
        encoding="utf-8",
    )


def _seed_frontend(workspace: Path) -> None:
    extension = workspace / "extension"
    extension.mkdir(parents=True, exist_ok=True)
    (extension / "manifest.json").write_text(
        json.dumps(
            {
                "manifest_version": 3,
                "name": "Idea Workspace Extension",
                "version": "0.1.0",
                "description": "Workspace extension scaffold",
            },
            indent=2,
        )
        + "\\n",
        encoding="utf-8",
    )


def _seed_e2e(workspace: Path) -> None:
    e2e = workspace / "tests" / "e2e"
    e2e.mkdir(parents=True, exist_ok=True)
    (e2e / "simulated_playwright.py").write_text(
        "\\n".join(
            [
                "#!/usr/bin/env python3",
                "def main() -> int:",
                "    return 0",
                "",
                "if __name__ == '__main__':",
                "    raise SystemExit(main())",
            ]
        )
        + "\\n",
        encoding="utf-8",
    )


def _run_google_probe(workspace: Path) -> Tuple[bool, str]:
    env_values = _load_env(workspace)
    require_google = env_values.get("SMARTBOOKMARKER_REQUIRE_GOOGLE_SHEETS_TEST", "1").strip().lower() not in {
        "0",
        "false",
        "no",
    }
    if not require_google:
        return True, "google_not_required"

    spreadsheet_id = env_values.get("GOOGLE_SHEETS_SPREADSHEET_ID", "").strip()
    creds_rel = env_values.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if not spreadsheet_id or not creds_rel:
        return False, "google_missing_config"

    creds_path = (workspace / creds_rel).resolve()
    if not creds_path.exists():
        return False, "google_credentials_not_found"

    try:
        from google.oauth2 import service_account  # type: ignore
        from googleapiclient.discovery import build  # type: ignore
    except Exception:
        return False, "google_libs_unavailable"

    try:
        creds = service_account.Credentials.from_service_account_file(
            str(creds_path),
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        tab = "integration_probe"
        meta = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            fields="sheets.properties.title",
        ).execute()
        titles = {
            str(item.get("properties", {}).get("title", ""))
            for item in meta.get("sheets", [])
            if isinstance(item, dict)
        }
        if tab not in titles:
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": [{"addSheet": {"properties": {"title": tab}}}]},
            ).execute()
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"{tab}!A:A",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [[f"integration probe {_utc_now()}"]]},
        ).execute()
        return True, f"google_sheets:{tab}"
    except Exception as exc:
        return False, f"google_write_failed:{exc.__class__.__name__}"


def _run_integration_checks(workspace: Path, artifacts_dir: Path) -> Dict[str, str]:
    backend_tests = workspace / "backend" / "tests"
    if backend_tests.exists():
        backend = subprocess.run(
            [sys.executable, "-m", "pytest", "backend/tests", "-q"],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=False,
        )
        backend_ok = backend.returncode == 0
        backend_output = (backend.stdout or "") + (backend.stderr or "")
    else:
        backend_ok = True
        backend_output = "backend/tests not present; skipped"

    e2e_script = workspace / "tests" / "e2e" / "simulated_playwright.py"
    if e2e_script.exists():
        e2e = subprocess.run(
            [sys.executable, str(e2e_script)],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=False,
        )
        e2e_ok = e2e.returncode == 0
        e2e_output = (e2e.stdout or "") + (e2e.stderr or "")
    else:
        e2e_ok = True
        e2e_output = "tests/e2e/simulated_playwright.py not present; skipped"

    google_ok, google_detail = _run_google_probe(workspace)

    report = artifacts_dir / "integration_test_report.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "\\n".join(
            [
                "# Integration Test Report",
                "",
                f"- Generated: `{_utc_now()}`",
                f"- Backend tests: `{'PASS' if backend_ok else 'FAIL'}`",
                f"- E2E simulation: `{'PASS' if e2e_ok else 'FAIL'}`",
                f"- Google Sheets communication: `{'PASS' if google_ok else 'FAIL'}`",
                f"- Google detail: `{google_detail}`",
                "",
                "## Backend Output",
                "```",
                backend_output.strip(),
                "```",
                "",
                "## E2E Output",
                "```",
                e2e_output.strip(),
                "```",
            ]
        )
        + "\\n",
        encoding="utf-8",
    )

    ok = backend_ok and e2e_ok and google_ok
    if ok:
        return {"review_status": "approved", "integration_loop_status": "passed"}

    return {
        "review_status": "changes_requested",
        "integration_loop_status": "failed",
        "integration_failure_target": "backend_engineer" if (not backend_ok or not google_ok) else "frontend_engineer",
    }


def run_step(role: str, phase: str, step_id: str, step_type: str, profile: str, artifacts_dir: Path) -> Dict[str, str]:
    workspace = _workspace()
    _append(
        workspace / "docs" / "adapter_execution_log.md",
        f"- `{_utc_now()}` role=`{role}` step=`{step_id}` phase=`{phase}` profile=`{profile}`\\n",
    )

    if role == "system_analyst":
        _append(workspace / "docs" / "requirements.md", "- requirements snapshot updated by adapter\\n")
    elif role == "architect":
        _append(workspace / "docs" / "architecture.md", "- architecture snapshot updated by adapter\\n")
    elif role == "backend_engineer":
        _seed_backend(workspace)
    elif role == "frontend_engineer":
        _seed_frontend(workspace)
    elif role == "qa_engineer":
        _seed_backend(workspace)
    elif role == "integration_tester":
        _seed_backend(workspace)
        _seed_e2e(workspace)
        return _run_integration_checks(workspace, artifacts_dir)
    elif role == "release_manager":
        _append(workspace / "docs" / "release_plan.md", "- release checklist prepared by adapter\\n")

    if step_type == "reviewer":
        return {"review_status": "approved"}
    return {}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="role_adapter.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run-step")
    p_run.add_argument("--role", required=True)
    p_run.add_argument("--phase", required=True)
    p_run.add_argument("--step-id", required=True)
    p_run.add_argument("--step-type", required=True)
    p_run.add_argument("--profile", required=True)
    p_run.add_argument("--artifacts-dir", required=True)
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    payload = run_step(
        role=args.role,
        phase=args.phase,
        step_id=args.step_id,
        step_type=args.step_type,
        profile=args.profile,
        artifacts_dir=Path(args.artifacts_dir),
    )
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
        encoding="utf-8",
    )


def _resolve_credentials_path(value: str, source_env_file: Path) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = (source_env_file.parent / candidate).resolve()
    return candidate


def _build_workspace_env(
    workspace: Path,
    allowlist_keys: List[str],
    source_env: Dict[str, str],
    source_env_file: Path,
) -> Dict[str, str]:
    missing = [key for key in allowlist_keys if key not in source_env or not source_env.get(key, "").strip()]
    if missing:
        raise WorkspaceBootstrapError(f"Missing required env keys: {', '.join(sorted(missing))}")

    out: Dict[str, str] = {}
    for key in allowlist_keys:
        out[key] = source_env[key]

    cred_key = "GOOGLE_APPLICATION_CREDENTIALS"
    if cred_key in out:
        src = _resolve_credentials_path(out[cred_key], source_env_file)
        if not src.exists():
            raise WorkspaceBootstrapError(
                f"Credentials file for {cred_key} not found: {src}"
            )
        dest = workspace / "secrets" / "google_credentials.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        out[cred_key] = "secrets/google_credentials.json"

    return out


def _write_env_file(workspace: Path, env_map: Dict[str, str]) -> None:
    lines = [f"{key}={value}" for key, value in env_map.items()]
    (workspace / ".env").write_text("\n".join(lines) + "\n", encoding="utf-8")


def bootstrap_workspace_for_idea(
    runtime_root: Path,
    idea_id: str,
    headline: str,
    source_env_file: Path = DEFAULT_SOURCE_ENV,
) -> Path:
    if not idea_id.strip():
        raise WorkspaceBootstrapError("Cannot bootstrap workspace without active idea_id.")

    idea_slug = orch_utils.slugify(idea_id) or "idea"
    workspace = runtime_root.parent / "implementations" / idea_slug

    for rel in [
        "adapter",
        "backend",
        "backend/tests",
        "extension",
        "tests/e2e",
        "docs",
        "artifacts",
        "secrets",
        ".orchestrator",
    ]:
        (workspace / rel).mkdir(parents=True, exist_ok=True)

    _write_gitignore(workspace)
    _write_workspace_readme(workspace, idea_id=idea_id, headline=headline)
    _write_role_adapter(workspace)

    allowlist = _load_allowlist(runtime_root / "rules" / "env_key_allowlist.txt")
    source_env = _parse_env_file(source_env_file)
    workspace_env = _build_workspace_env(
        workspace=workspace,
        allowlist_keys=allowlist,
        source_env=source_env,
        source_env_file=source_env_file,
    )
    _write_env_file(workspace, workspace_env)
    _ensure_git_initialized(workspace, idea_id=idea_id)
    return workspace
