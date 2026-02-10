#!/usr/bin/env python3
"""Tests for Version2 profile-driven orchestrator hard guards."""

import argparse
import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = TOOLS_DIR / "src"
sys.path.insert(0, str(SRC_DIR))
ORCHESTRATOR_PATH = SRC_DIR / "orchestrator" / "main.py"
SPEC = importlib.util.spec_from_file_location("version2_orchestrator_under_test", ORCHESTRATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Failed to load orchestrator module from {ORCHESTRATOR_PATH}")
o2 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = o2
SPEC.loader.exec_module(o2)


def _profile():
    return o2.load_and_validate_profile("default_fallback_profile")


def _status(profile):
    return o2.setup_from_profile({}, profile, "default_fallback_profile", "test")


def _realization_profile():
    return o2.load_and_validate_profile("smartbookmarker_realization")


def test_profile_validation_passes():
    profile = _profile()
    assert profile["name"] == "default_fallback_profile"


def test_invalid_profile_has_friendly_error():
    with pytest.raises(o2.OrchestratorV2Error) as exc:
        o2.load_and_validate_profile("not_real")
    assert "Available profiles" in str(exc.value)


def test_illegal_transition_rejected():
    status = _status(_profile())
    status["current_role"] = "wrong_role"
    with pytest.raises(o2.OrchestratorV2Error) as exc:
        o2.step_once(status, _profile())
    assert "Illegal transition state" in str(exc.value)


def test_missing_required_outputs_rejected():
    status = _status(_profile())
    status["role_status"] = "completed"
    status["artifacts"] = {}
    with pytest.raises(o2.OrchestratorV2Error) as exc:
        o2.step_once(status, _profile())
    assert "Missing required outputs" in str(exc.value)


def test_review_cycle_cap_blocks_and_escalates():
    profile = _profile()
    status = _status(profile)

    # Move to reviewer step.
    status["current_step_index"] = 1
    step = status["phase_plan"][1]
    status["current_phase"] = step["phase"]
    status["current_role"] = step["role"]
    status["phase_status"] = "awaiting_review"
    status["role_status"] = "completed"
    status["review_status"] = "changes_requested"
    status["review_cycles"] = {"requirements": 2}

    result = o2.step_once(status, profile)
    assert result.outcome == "blocked"
    assert any("Review cycle cap exceeded" in reason for reason in status["blocking_reasons"])


def test_gate_step_waits_for_human_approval():
    profile = _profile()
    status = _status(profile)

    # Force status to requirements gate step.
    status["current_step_index"] = 2
    step = status["phase_plan"][2]
    status["current_phase"] = step["phase"]
    status["current_role"] = step["role"]
    status["phase_status"] = "in_progress"
    status["role_status"] = "in_progress"

    result = o2.step_once(status, profile)
    assert result.outcome == "blocked"
    assert any("REQ_FREEZE_APPROVAL" in reason for reason in status["blocking_reasons"])


def test_deterministic_replay_for_same_input_state():
    profile = _profile()
    baseline = _status(profile)
    baseline["role_status"] = "completed"
    baseline["artifacts"] = {
        "acceptance_contract.md": {
            "path": "agent_runtime/artifacts/acceptance_contract.md",
            "owner": "system_analyst",
            "updated_at": "2026-02-07T22:00:00Z",
        },
        "traceability_map.md": {
            "path": "agent_runtime/artifacts/traceability_map.md",
            "owner": "system_analyst",
            "updated_at": "2026-02-07T22:00:00Z",
        },
    }

    first = deepcopy(baseline)
    second = deepcopy(baseline)

    r1 = o2.step_once(first, profile)
    r2 = o2.step_once(second, profile)

    assert r1.outcome == r2.outcome
    assert first["current_step_index"] == second["current_step_index"]
    assert first["current_phase"] == second["current_phase"]
    assert first["current_role"] == second["current_role"]


def test_run_default_policy_stops_at_release_approval(monkeypatch, tmp_path):
    monkeypatch.delenv("ORCHESTRATOR_MIDFLOW_HUMAN_GATES", raising=False)

    profile = _profile()
    status = _status(profile)
    status_file = tmp_path / "status.json"
    trace_file = tmp_path / "trace.csv"
    o2.save_json(status_file, status)

    code = o2.cmd_run(
        argparse.Namespace(
            status_file=str(status_file),
            trace_file=str(trace_file),
            max_steps=250,
        )
    )
    assert code == 0

    latest = o2.load_json(status_file)
    assert latest["current_phase"] == "release"
    assert latest["current_role"] == "human_engineer"
    assert latest["phase_status"] == "waiting"
    assert latest["realization_status"] == "waiting_approval"
    assert latest["pending_human_gate_id"] == "RELEASE_APPROVAL"
    assert latest["pending_human_question_id"].startswith("Q-GATE-RELEASE_APPROVAL-")

    gate_questions = [q for q in latest.get("questions", []) if q.get("gate_id") == "RELEASE_APPROVAL"]
    assert len(gate_questions) == 1
    assert gate_questions[0]["status"] == "pending_delivery"


def test_run_writes_artifacts_under_active_idea_slug(monkeypatch, tmp_path):
    monkeypatch.delenv("ORCHESTRATOR_MIDFLOW_HUMAN_GATES", raising=False)

    status = _status(_profile())
    status["active_idea_id"] = "smartbookmarker_ai_powered_boo"
    status["active_idea_headline"] = "SmartBookmarker: AI-Powered Bookmark Organizer"

    status_file = tmp_path / "status.json"
    o2.save_json(status_file, status)

    code = o2.cmd_run(
        argparse.Namespace(
            status_file=str(status_file),
            trace_file="",
            max_steps=250,
        )
    )
    assert code == 0

    latest = o2.load_json(status_file)
    assert latest.get("artifacts")

    expected_dir = tmp_path / "artifacts" / "smartbookmarker_ai_powered_bookmark_organizer"
    for meta in latest["artifacts"].values():
        assert str(expected_dir) in str(meta.get("path", ""))

    assert (expected_dir / "03_transition_trace.csv").exists()


def test_run_midflow_human_gate_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("ORCHESTRATOR_MIDFLOW_HUMAN_GATES", "REQ_FREEZE_APPROVAL")

    status = _status(_profile())
    status_file = tmp_path / "status.json"
    trace_file = tmp_path / "trace.csv"
    o2.save_json(status_file, status)

    code = o2.cmd_run(
        argparse.Namespace(
            status_file=str(status_file),
            trace_file=str(trace_file),
            max_steps=50,
        )
    )
    assert code == 0

    latest = o2.load_json(status_file)
    assert latest["current_phase"] == "requirements"
    assert latest["current_role"] == "human_engineer"
    assert latest["phase_status"] == "waiting"
    assert latest["pending_human_gate_id"] == "REQ_FREEZE_APPROVAL"
    assert latest["pending_human_question_id"].startswith("Q-GATE-REQ_FREEZE_APPROVAL-")


def test_run_waiting_gate_is_idempotent_without_duplicate_question(monkeypatch, tmp_path):
    monkeypatch.setenv("ORCHESTRATOR_MIDFLOW_HUMAN_GATES", "REQ_FREEZE_APPROVAL")

    status = _status(_profile())
    status_file = tmp_path / "status.json"
    trace_file = tmp_path / "trace.csv"
    o2.save_json(status_file, status)

    args = argparse.Namespace(status_file=str(status_file), trace_file=str(trace_file), max_steps=50)
    o2.cmd_run(args)
    first = o2.load_json(status_file)
    first_qid = first["pending_human_question_id"]
    first_count = len([q for q in first.get("questions", []) if q.get("gate_id") == "REQ_FREEZE_APPROVAL"])
    assert first_count == 1

    o2.cmd_run(args)
    second = o2.load_json(status_file)
    second_qid = second["pending_human_question_id"]
    second_count = len([q for q in second.get("questions", []) if q.get("gate_id") == "REQ_FREEZE_APPROVAL"])
    assert second_count == 1
    assert second_qid == first_qid


def test_run_resume_after_release_approval_reaches_done(monkeypatch, tmp_path):
    monkeypatch.delenv("ORCHESTRATOR_MIDFLOW_HUMAN_GATES", raising=False)

    status = _status(_profile())
    status_file = tmp_path / "status.json"
    trace_file = tmp_path / "trace.csv"
    o2.save_json(status_file, status)

    run_args = argparse.Namespace(status_file=str(status_file), trace_file=str(trace_file), max_steps=250)
    o2.cmd_run(run_args)

    set_args = argparse.Namespace(
        status_file=str(status_file),
        gate_id="RELEASE_APPROVAL",
        decision="approved",
        reason="Approved in unit test",
    )
    o2.cmd_set_gate(set_args)
    o2.cmd_run(run_args)

    latest = o2.load_json(status_file)
    assert latest["current_phase"] == "done"
    assert latest["realization_status"] == "completed"


def test_realization_profile_is_valid():
    profile = _realization_profile()
    assert profile["execution_mode"] == "realization"


def test_init_realization_bootstraps_workspace(monkeypatch, tmp_path):
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
    monkeypatch.setenv("ORCHESTRATOR_SOURCE_ENV", str(source_env))

    runtime = tmp_path / "runtime"
    (runtime / "rules").mkdir(parents=True, exist_ok=True)
    (runtime / "rules" / "env_key_allowlist.txt").write_text(
        "\n".join(
            [
                "AI_API_KEY",
                "GOOGLE_SHEETS_SPREADSHEET_ID",
                "GOOGLE_APPLICATION_CREDENTIALS",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    status_file = runtime / "status.json"

    code = o2.cmd_init(
        argparse.Namespace(
            invocation="/orchestrator @smartbookmarker_realization",
            status_file=str(status_file),
            charter_version="test",
            idea_id="smartbookmarker_ai_powered_boo",
            idea_headline="SmartBookmarker: AI-Powered Bookmark Organizer",
        )
    )
    assert code == 0

    status = o2.load_json(status_file)
    assert status["execution_mode"] == "realization"
    assert status["workspace_git_initialized"] is True
    workspace = Path(status["workspace_dir"])
    assert workspace.exists()
    assert (workspace / ".git").exists()
    assert (workspace / ".env").exists()
    assert (workspace / "secrets" / "google_credentials.json").exists()
    env_text = (workspace / ".env").read_text(encoding="utf-8")
    assert "GOOGLE_APPLICATION_CREDENTIALS=secrets/google_credentials.json" in env_text


def test_run_realization_writes_commit_ledger(monkeypatch, tmp_path):
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
    monkeypatch.setenv("ORCHESTRATOR_SOURCE_ENV", str(source_env))
    monkeypatch.delenv("ORCHESTRATOR_MIDFLOW_HUMAN_GATES", raising=False)

    runtime = tmp_path / "runtime"
    (runtime / "rules").mkdir(parents=True, exist_ok=True)
    (runtime / "rules" / "env_key_allowlist.txt").write_text(
        "AI_API_KEY\nGOOGLE_SHEETS_SPREADSHEET_ID\nGOOGLE_APPLICATION_CREDENTIALS\n",
        encoding="utf-8",
    )
    status_file = runtime / "status.json"

    o2.cmd_init(
        argparse.Namespace(
            invocation="/orchestrator @smartbookmarker_realization",
            status_file=str(status_file),
            charter_version="test",
            idea_id="smartbookmarker_ai_powered_boo",
            idea_headline="SmartBookmarker: AI-Powered Bookmark Organizer",
        )
    )
    code = o2.cmd_run(
        argparse.Namespace(
            status_file=str(status_file),
            trace_file="",
            max_steps=1,
        )
    )
    assert code == 0

    status = o2.load_json(status_file)
    assert status["commit_evidence"]
    artifacts_dir = runtime / "artifacts" / "smartbookmarker_ai_powered_bookmark_organizer"
    assert (artifacts_dir / "10_commit_ledger.md").exists()


def test_run_realization_blocks_if_no_new_commit(monkeypatch, tmp_path):
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
    monkeypatch.setenv("ORCHESTRATOR_SOURCE_ENV", str(source_env))

    runtime = tmp_path / "runtime"
    (runtime / "rules").mkdir(parents=True, exist_ok=True)
    (runtime / "rules" / "env_key_allowlist.txt").write_text(
        "AI_API_KEY\nGOOGLE_SHEETS_SPREADSHEET_ID\nGOOGLE_APPLICATION_CREDENTIALS\n",
        encoding="utf-8",
    )
    status_file = runtime / "status.json"

    o2.cmd_init(
        argparse.Namespace(
            invocation="/orchestrator @smartbookmarker_realization",
            status_file=str(status_file),
            charter_version="test",
            idea_id="smartbookmarker_ai_powered_boo",
            idea_headline="SmartBookmarker: AI-Powered Bookmark Organizer",
        )
    )

    def _fake_execute(status, step, profile_name, artifacts_dir=None, workspace_dir=None, execution_mode="simulation"):
        status["role_status"] = "completed"
        now = "2026-02-08T00:00:00Z"
        for output_name in step.get("required_outputs", []):
            status.setdefault("artifacts", {})[output_name] = {
                "path": str((artifacts_dir or tmp_path) / output_name),
                "owner": step.get("role", "unknown"),
                "updated_at": now,
            }
        return step.get("required_outputs", [])

    monkeypatch.setattr(o2, "execute_role_step", _fake_execute)
    code = o2.cmd_run(
        argparse.Namespace(
            status_file=str(status_file),
            trace_file="",
            max_steps=1,
        )
    )
    assert code == 0
    status = o2.load_json(status_file)
    assert status["phase_status"] == "blocked"
    assert any("Git protocol violation" in reason for reason in status.get("blocking_reasons", []))


def test_parse_trigger_command_rejects_typo_alias():
    with pytest.raises(o2.OrchestratorV2Error):
        o2.parse_trigger_command("/orchestor")


def test_parse_trigger_command_uses_default_fallback_profile(monkeypatch):
    monkeypatch.delenv("ORCHESTRATOR_PROFILE", raising=False)
    assert o2.parse_trigger_command("/orchestrator") == "default_fallback_profile"


def test_trigger_forces_idea_activated_and_runs(monkeypatch, tmp_path):
    context = tmp_path / "context.md"
    context.write_text(
        "\n".join(
            [
                "---",
                "idea_id: smartbookmarker_ai_powered_boo",
                "---",
                "",
                "context",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    ideas_dir = tmp_path / "ideas"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    idea_file = ideas_dir / "smartbookmarker_ai_powered_boo.md"
    idea_file.write_text(
        "\n".join(
            [
                "## ID: smartbookmarker_ai_powered_boo",
                "**Headline:** SmartBookmarker: AI-Powered Bookmark Organizer",
                "**Status:** DONE",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    calls = {"init": 0, "run": 0}

    def _fake_init(_args):
        calls["init"] += 1
        return 0

    def _fake_run(_args):
        calls["run"] += 1
        return 0

    monkeypatch.setattr(o2, "cmd_init", _fake_init)
    monkeypatch.setattr(o2, "cmd_run", _fake_run)

    code = o2.cmd_trigger(
        argparse.Namespace(
            command="/orchestrator @smartbookmarker_realization",
            status_file=str(tmp_path / "status.json"),
            charter_version="test",
            max_steps=10,
            trace_file="",
            context_file=str(context),
            ideas_dir=str(ideas_dir),
        )
    )
    assert code == 0
    assert calls["init"] == 1
    assert calls["run"] == 1
    assert "**Status:** ACTIVATED" in idea_file.read_text(encoding="utf-8")


def test_resolve_active_idea_id_missing_fails(tmp_path):
    context = tmp_path / "context.md"
    context.write_text(
        "\n".join(["---", "plugin: smartbookmarker", "---", ""]) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(o2.OrchestratorV2Error):
        o2.resolve_active_idea_id(context)


def test_init_with_relative_status_path_writes_absolute_workspace(monkeypatch, tmp_path):
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
    monkeypatch.setenv("ORCHESTRATOR_SOURCE_ENV", str(source_env))
    monkeypatch.chdir(tmp_path)

    runtime = tmp_path / "runtime"
    (runtime / "rules").mkdir(parents=True, exist_ok=True)
    (runtime / "rules" / "env_key_allowlist.txt").write_text(
        "AI_API_KEY\nGOOGLE_SHEETS_SPREADSHEET_ID\nGOOGLE_APPLICATION_CREDENTIALS\n",
        encoding="utf-8",
    )

    code = o2.cmd_init(
        argparse.Namespace(
            invocation="/orchestrator @smartbookmarker_realization",
            status_file="runtime/status.json",
            charter_version="test",
            idea_id="expense_tracker",
            idea_headline="Expense Tracker",
        )
    )
    assert code == 0

    status = o2.load_json(runtime / "status.json")
    assert Path(status["workspace_dir"]).is_absolute()
