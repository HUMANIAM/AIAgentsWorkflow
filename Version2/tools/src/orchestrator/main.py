#!/usr/bin/env python3
"""Version2 profile-driven orchestrator with hard guards."""

from __future__ import annotations

import argparse
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

SRC_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = Path(__file__).resolve().parents[2]
ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.role_executor import execute_step as execute_role_step
from orchestrator.workspace_bootstrap import (
    DEFAULT_SOURCE_ENV,
    WorkspaceBootstrapError,
    bootstrap_workspace_for_idea,
)
from orchestrator import git_protocol as orch_git
from orchestrator import state_machine as orch_state
from orchestrator import utils as orch_utils
from orchestrator import validation as orch_validation


RUNTIME = ROOT / "agent_runtime"
PROFILES_DIR = RUNTIME / "workflow_profiles"
PROFILE_SCHEMA_PATH = RUNTIME / "schemas" / "workflow_profile.schema.json"
STATUS_SCHEMA_PATH = RUNTIME / "schemas" / "status.schema.json"
DEFAULT_STATUS = RUNTIME / "status.json"
DEFAULT_CONTEXT = RUNTIME / "plugin" / "context.md"
DEFAULT_IDEAS_DIR = RUNTIME / "ideas"

class OrchestratorV2Error(Exception):
    """Friendly orchestrator runtime error."""


StepResult = orch_state.StepResult


def utc_now() -> str:
    return orch_utils.utc_now()


def slugify(value: str) -> str:
    return orch_utils.slugify(value)


def artifact_slug_from_status(status: Dict[str, Any]) -> str:
    return orch_utils.artifact_slug_from_status(status)


def resolve_artifacts_dir(status: Dict[str, Any], runtime_root: Path) -> Path:
    return orch_utils.resolve_artifacts_dir(status, runtime_root)


def resolve_trace_path(
    trace_file_arg: Optional[str],
    status: Dict[str, Any],
    runtime_root: Path,
) -> Path:
    return orch_utils.resolve_trace_path(trace_file_arg, status, runtime_root)


def load_json(path: Path) -> Dict[str, Any]:
    try:
        return orch_validation.load_json(path)
    except ValueError as exc:
        raise OrchestratorV2Error(str(exc)) from exc


def save_json(path: Path, data: Dict[str, Any]) -> None:
    orch_validation.save_json(path, data)


def load_yaml(path: Path) -> Dict[str, Any]:
    try:
        return orch_validation.load_yaml(path)
    except ValueError as exc:
        raise OrchestratorV2Error(str(exc)) from exc


def load_schema(path: Path) -> Dict[str, Any]:
    return orch_validation.load_schema(path)


def list_profiles() -> List[str]:
    return orch_validation.list_profiles(PROFILES_DIR)


def parse_invocation(invocation: str) -> str:
    return orch_utils.parse_invocation(
        invocation,
        list_profiles_fn=list_profiles,
        error_cls=OrchestratorV2Error,
    )


def parse_trigger_command(command: str) -> str:
    return orch_utils.parse_trigger_command(
        command,
        default_profile="default_fallback_profile",
        error_cls=OrchestratorV2Error,
    )


def _parse_front_matter(text: str) -> Dict[str, str]:
    return orch_utils.parse_front_matter(text)


def resolve_active_idea_id(context_path: Path) -> str:
    return orch_utils.resolve_active_idea_id(context_path, error_cls=OrchestratorV2Error)


def read_idea_headline_and_status(idea_path: Path) -> tuple[str, str]:
    return orch_utils.read_idea_headline_and_status(idea_path, error_cls=OrchestratorV2Error)


def force_idea_status(idea_path: Path, status_value: str) -> None:
    orch_utils.force_idea_status(idea_path, status_value)


def load_and_validate_profile(profile_name: str) -> Dict[str, Any]:
    return orch_validation.load_and_validate_profile(
        profile_name,
        profiles_dir=PROFILES_DIR,
        profile_schema_path=PROFILE_SCHEMA_PATH,
        error_cls=OrchestratorV2Error,
        list_profiles_fn=list_profiles,
    )


def compile_phase_plan(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    return orch_state.compile_phase_plan(profile)


def gate_map(status: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return orch_state.gate_map(status)


def parse_midflow_human_gates(raw: str) -> Set[str]:
    return orch_utils.parse_midflow_human_gates(raw)


def human_required_gates() -> Set[str]:
    return orch_utils.human_required_gates()


def is_done(status: Dict[str, Any]) -> bool:
    return orch_utils.is_done(status)


def find_open_gate_question(status: Dict[str, Any], gate_id: str) -> str:
    return orch_utils.find_open_gate_question(status, gate_id)


def ensure_gate_question(status: Dict[str, Any], gate_id: str, step: Dict[str, Any]) -> str:
    return orch_utils.ensure_gate_question(status, gate_id, step, now_fn=utc_now)


def setup_from_profile(
    status: Dict[str, Any],
    profile: Dict[str, Any],
    profile_name: str,
    charter_version: str,
) -> Dict[str, Any]:
    return orch_state.setup_from_profile(
        status,
        profile,
        profile_name,
        charter_version,
        now_fn=utc_now,
        error_cls=OrchestratorV2Error,
    )


def validate_status(status: Dict[str, Any]) -> None:
    orch_validation.validate_status(
        status,
        status_schema_path=STATUS_SCHEMA_PATH,
        error_cls=OrchestratorV2Error,
    )


def find_missing_outputs(status: Dict[str, Any], step: Dict[str, Any]) -> List[str]:
    return orch_state.find_missing_outputs(status, step)


def unresolved_required_questions(status: Dict[str, Any]) -> List[str]:
    return orch_state.unresolved_required_questions(status)


def unresolved_critical_failures(status: Dict[str, Any]) -> List[str]:
    return orch_state.unresolved_critical_failures(status)


def get_current_step(status: Dict[str, Any]) -> Dict[str, Any]:
    return orch_state.get_current_step(status, error_cls=OrchestratorV2Error)


def profile_max_review_cycles(profile: Dict[str, Any]) -> int:
    return orch_state.profile_max_review_cycles(profile)


def producer_index_for_reviewer(status: Dict[str, Any], reviewer_step: Dict[str, Any]) -> int:
    return orch_state.producer_index_for_reviewer(
        status,
        reviewer_step,
        error_cls=OrchestratorV2Error,
    )


def move_to_step(status: Dict[str, Any], target_idx: int, from_step_id: str) -> None:
    orch_state.move_to_step(status, target_idx, from_step_id, now_fn=utc_now)


def compute_blocking(status: Dict[str, Any], step: Dict[str, Any]) -> List[str]:
    return orch_state.compute_blocking(status, step)


def step_once(status: Dict[str, Any], profile: Dict[str, Any]) -> StepResult:
    return orch_state.step_once(
        status,
        profile,
        now_fn=utc_now,
        error_cls=OrchestratorV2Error,
    )


def append_trace(trace_path: Path, from_status: Dict[str, Any], to_status: Dict[str, Any], result: StepResult) -> None:
    orch_utils.append_trace(trace_path, from_status, to_status, result)


def _git_head(workspace: Path) -> str:
    return orch_git.collect_head_sha(workspace)


def _validate_step_commit(
    workspace: Path,
    pre_sha: str,
    role: str,
) -> Optional[str]:
    return orch_git.validate_step_commit(workspace, pre_sha, role)


def write_commit_ledger(status: Dict[str, Any], artifacts_dir: Path) -> None:
    orch_git.write_commit_ledger(status, artifacts_dir, now_fn=utc_now)


def _resolve_cli_path(raw: str, *, base: Optional[Path] = None) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (base or Path.cwd()) / path
    return path.resolve()


def _resolve_env_path(raw: str, *, fallback: Path, base: Path) -> Path:
    value = str(raw or "").strip()
    path = Path(value).expanduser() if value else fallback
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def cmd_list_profiles(_args: argparse.Namespace) -> int:
    names = list_profiles()
    if not names:
        print("No workflow profiles found.")
        return 1
    print("Available profiles:")
    for name in names:
        print(f"- {name}")
    return 0


def cmd_validate_profile(args: argparse.Namespace) -> int:
    load_and_validate_profile(args.profile)
    print(f"Profile '{args.profile}' is valid.")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    profile_name = parse_invocation(args.invocation)
    profile = load_and_validate_profile(profile_name)

    status_path = _resolve_cli_path(args.status_file)
    base_status: Dict[str, Any] = {}
    if status_path.exists():
        base_status = load_json(status_path)

    if args.idea_id:
        base_status["active_idea_id"] = str(args.idea_id).strip()
    if args.idea_headline is not None:
        base_status["active_idea_headline"] = str(args.idea_headline)
    if base_status.get("active_idea_id") and "active_idea" not in base_status:
        base_status["active_idea"] = {
            "id": base_status.get("active_idea_id", ""),
            "headline": base_status.get("active_idea_headline", ""),
            "owner_user_id": None,
            "context_file": f"plugin/context_{base_status.get('active_idea_id', '')}.md",
            "executed_at": utc_now(),
            "profile": profile_name,
        }

    status = setup_from_profile(base_status, profile, profile_name, args.charter_version)

    if status.get("execution_mode") == "realization":
        idea_id = str(status.get("active_idea_id", "")).strip()
        idea_headline = str(status.get("active_idea_headline", "")).strip()
        source_env = _resolve_env_path(
            os.getenv("ORCHESTRATOR_SOURCE_ENV", ""),
            fallback=DEFAULT_SOURCE_ENV,
            base=ROOT,
        )
        try:
            workspace = bootstrap_workspace_for_idea(
                runtime_root=status_path.parent,
                idea_id=idea_id,
                headline=idea_headline or idea_id,
                source_env_file=source_env,
            )
        except WorkspaceBootstrapError as exc:
            raise OrchestratorV2Error(f"Realization workspace bootstrap failed: {exc}") from exc

        status["workspace_dir"] = str(workspace.resolve())
        status["workspace_git_initialized"] = True
        status["integration_loop_status"] = "idle"

    validate_status(status)
    save_json(status_path, status)
    print(
        "Initialized flow: "
        f"profile={profile_name} step=0 role={status['current_role']} phase={status['current_phase']} "
        f"mode={status.get('execution_mode')}"
    )
    return 0


def cmd_validate_status(args: argparse.Namespace) -> int:
    status = load_json(_resolve_cli_path(args.status_file))
    validate_status(status)
    print("status.json is valid.")
    return 0


def cmd_set_gate(args: argparse.Namespace) -> int:
    status_path = _resolve_cli_path(args.status_file)
    status = load_json(status_path)
    validate_status(status)

    found = False
    for gate in status.get("governance_gates", []):
        if isinstance(gate, dict) and gate.get("id") == args.gate_id:
            gate["status"] = args.decision
            gate["reason"] = args.reason
            gate["updated_at"] = utc_now()
            found = True
            break

    if not found:
        gate_ids = [g.get("id") for g in status.get("governance_gates", []) if isinstance(g, dict)]
        raise OrchestratorV2Error(
            f"Unknown gate '{args.gate_id}'. Valid gates: {', '.join(sorted(map(str, gate_ids)))}"
        )

    gate_id_upper = str(args.gate_id).upper()
    answered_gate_question_ids: List[str] = []
    if args.decision in {"approved", "rejected"}:
        for q in status.get("questions", []):
            if not isinstance(q, dict):
                continue
            if str(q.get("gate_id", "")).upper() != gate_id_upper:
                continue
            if q.get("status") in {"pending_delivery", "delivered"}:
                q["status"] = "answered"
                qid = q.get("id")
                if isinstance(qid, str) and qid:
                    answered_gate_question_ids.append(qid)

        existing_answer_ids = {
            a.get("question_id")
            for a in status.get("answers", [])
            if isinstance(a, dict) and isinstance(a.get("question_id"), str)
        }
        for qid in answered_gate_question_ids:
            if qid in existing_answer_ids:
                continue
            status.setdefault("answers", []).append(
                {
                    "question_id": qid,
                    "answer": f"Gate set to {args.decision} via set-gate command.",
                    "source": "orchestrator_cli",
                    "answered_at": utc_now(),
                }
            )

    if args.decision == "approved":
        status["pending_human_gate_id"] = ""
        if status.get("pending_human_question_id") in answered_gate_question_ids:
            status["pending_human_question_id"] = ""
        if gate_id_upper == "RELEASE_APPROVAL":
            status["realization_status"] = "approved"
    elif args.decision == "rejected":
        status["pending_human_gate_id"] = args.gate_id
        if gate_id_upper == "RELEASE_APPROVAL":
            status["realization_status"] = "rejected"

    save_json(status_path, status)
    print(f"Gate '{args.gate_id}' set to {args.decision}.")
    return 0


def cmd_step(args: argparse.Namespace) -> int:
    status_path = _resolve_cli_path(args.status_file)
    status = load_json(status_path)
    validate_status(status)
    trace_path = resolve_trace_path(args.trace_file, status, runtime_root=status_path.parent)

    profile_name = status.get("active_profile")
    if not isinstance(profile_name, str) or not profile_name:
        raise OrchestratorV2Error("status.json missing active_profile. Initialize flow first.")

    profile = load_and_validate_profile(profile_name)

    from_status = deepcopy(status)
    result = step_once(status, profile)
    validate_status(status)
    save_json(status_path, status)
    append_trace(trace_path, from_status, status, result)

    print(f"[{result.outcome}] {result.message}")
    print(
        f"cursor: step={status.get('current_step_index')} "
        f"phase={status.get('current_phase')} role={status.get('current_role')}"
    )
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    status_path = _resolve_cli_path(args.status_file)
    status = load_json(status_path)
    validate_status(status)
    artifacts_dir = resolve_artifacts_dir(status, runtime_root=status_path.parent)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    trace_path = resolve_trace_path(args.trace_file, status, runtime_root=status_path.parent)

    profile_name = status.get("active_profile")
    if not isinstance(profile_name, str) or not profile_name:
        raise OrchestratorV2Error("status.json missing active_profile. Initialize flow first.")
    profile = load_and_validate_profile(profile_name)

    execution_mode = str(status.get("execution_mode", "simulation")).strip().lower()
    workspace_dir: Optional[Path] = None
    if execution_mode == "realization":
        workspace = str(status.get("workspace_dir", "")).strip()
        if not workspace:
            raise OrchestratorV2Error("Realization mode requires workspace_dir in status.")
        workspace_dir = Path(workspace).expanduser()
        if not workspace_dir.is_absolute():
            workspace_dir = (ROOT / workspace_dir).resolve()
        else:
            workspace_dir = workspace_dir.resolve()
        if not workspace_dir.exists():
            raise OrchestratorV2Error(f"workspace_dir does not exist: {workspace_dir}")
        if not (workspace_dir / ".git").exists():
            raise OrchestratorV2Error(f"workspace_dir is not a git repository: {workspace_dir}")
        status["workspace_dir"] = str(workspace_dir)
        status["integration_loop_status"] = "running"

    if not str(status.get("realization_status", "")).strip():
        status["realization_status"] = "executing"

    required_human = human_required_gates()
    max_steps = int(args.max_steps)
    if max_steps <= 0:
        raise OrchestratorV2Error("--max-steps must be > 0.")

    steps = 0
    while steps < max_steps:
        if is_done(status):
            if status.get("realization_status") != "rejected":
                status["realization_status"] = "completed"
            if execution_mode == "realization":
                status["integration_loop_status"] = "passed"
            validate_status(status)
            save_json(status_path, status)
            print("Flow already complete. Nothing to run.")
            return 0

        step = get_current_step(status)
        from_status = deepcopy(status)
        step_type = str(step.get("step_type", ""))

        if step_type == "gate":
            gate_id = str(step.get("gate", "")).upper()
            gate = gate_map(status).get(gate_id)
            if not gate:
                raise OrchestratorV2Error(f"Missing gate definition in status for {gate_id}.")

            if gate.get("status") == "pending" and gate_id in required_human:
                qid = ensure_gate_question(status, gate_id, step)
                status["phase_status"] = "waiting"
                status["role_status"] = "in_progress"
                status["blocking_reasons"] = [f"Awaiting human approval for gate: {gate_id}"]
                status["pending_human_gate_id"] = gate_id
                if gate_id == "RELEASE_APPROVAL":
                    status["realization_status"] = "waiting_approval"
                result = StepResult(
                    changed=False,
                    outcome="blocked",
                    message=f"Human approval required for gate {gate_id}; question={qid}.",
                )
                validate_status(status)
                save_json(status_path, status)
                append_trace(trace_path, from_status, status, result)
                write_commit_ledger(status, artifacts_dir)
                print(f"[{result.outcome}] {result.message}")
                print(
                    f"cursor: step={status.get('current_step_index')} "
                    f"phase={status.get('current_phase')} role={status.get('current_role')}"
                )
                return 0

            if gate.get("status") == "pending":
                gate["status"] = "approved"
                gate["reason"] = "Auto-approved by orchestrator policy."
                gate["updated_at"] = utc_now()

            if gate_id == "RELEASE_APPROVAL" and gate.get("status") == "approved":
                status["realization_status"] = "approved"

        else:
            pre_blocking = compute_blocking(status, step)
            if pre_blocking:
                status["blocking_reasons"] = pre_blocking
                status["phase_status"] = "waiting"
                status["last_failed_role"] = str(step.get("role", ""))
                result = StepResult(changed=False, outcome="blocked", message=" ; ".join(pre_blocking))
                validate_status(status)
                save_json(status_path, status)
                append_trace(trace_path, from_status, status, result)
                write_commit_ledger(status, artifacts_dir)
                print(f"[{result.outcome}] {result.message}")
                print(
                    f"cursor: step={status.get('current_step_index')} "
                    f"phase={status.get('current_phase')} role={status.get('current_role')}"
                )
                return 0

            pre_sha = _git_head(workspace_dir) if workspace_dir else ""
            execute_role_step(
                status,
                step,
                profile_name=profile_name,
                artifacts_dir=artifacts_dir,
                workspace_dir=workspace_dir,
                execution_mode=execution_mode,
            )
            if workspace_dir:
                violation = _validate_step_commit(
                    workspace=workspace_dir,
                    pre_sha=pre_sha,
                    role=str(step.get("role", "")),
                )
                if violation:
                    status["phase_status"] = "blocked"
                    status["blocking_reasons"] = [violation]
                    status["last_failed_role"] = str(step.get("role", ""))
                    status["integration_loop_status"] = "failed"
                    result = StepResult(False, "blocked", violation)
                    validate_status(status)
                    save_json(status_path, status)
                    append_trace(trace_path, from_status, status, result)
                    write_commit_ledger(status, artifacts_dir)
                    print(f"[{result.outcome}] {result.message}")
                    print(
                        f"cursor: step={status.get('current_step_index')} "
                        f"phase={status.get('current_phase')} role={status.get('current_role')}"
                    )
                    return 0

        result = step_once(status, profile)
        validate_status(status)
        save_json(status_path, status)
        append_trace(trace_path, from_status, status, result)
        write_commit_ledger(status, artifacts_dir)
        steps += 1

        if result.outcome in {"blocked", "waiting"}:
            print(f"[{result.outcome}] {result.message}")
            print(
                f"cursor: step={status.get('current_step_index')} "
                f"phase={status.get('current_phase')} role={status.get('current_role')}"
            )
            return 0

    print(f"Reached max steps ({max_steps}).")
    print(
        f"cursor: step={status.get('current_step_index')} "
        f"phase={status.get('current_phase')} role={status.get('current_role')}"
    )
    return 0


def cmd_trigger(args: argparse.Namespace) -> int:
    profile = parse_trigger_command(args.command)

    context_path = _resolve_cli_path(args.context_file)
    ideas_dir = _resolve_cli_path(args.ideas_dir)
    status_path = _resolve_cli_path(args.status_file)

    idea_id = resolve_active_idea_id(context_path)
    idea_path = ideas_dir / f"{idea_id}.md"
    headline, _status = read_idea_headline_and_status(idea_path)

    # Keep parity with previous wrapper behavior: force run start in ACTIVATED state.
    force_idea_status(idea_path, "ACTIVATED")

    init_args = argparse.Namespace(
        invocation=f"/orchestrator @{profile}",
        status_file=str(status_path),
        charter_version=args.charter_version,
        idea_id=idea_id,
        idea_headline=headline,
    )
    init_code = cmd_init(init_args)
    if init_code != 0:
        return init_code

    run_args = argparse.Namespace(
        status_file=str(status_path),
        trace_file=args.trace_file,
        max_steps=args.max_steps,
    )
    return cmd_run(run_args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tools/src/orchestrator/main.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list-profiles", help="List available workflow profiles")
    p_list.set_defaults(func=cmd_list_profiles)

    p_vp = sub.add_parser("validate-profile", help="Validate a workflow profile")
    p_vp.add_argument("profile")
    p_vp.set_defaults(func=cmd_validate_profile)

    p_init = sub.add_parser("init", help="Initialize status from invocation")
    p_init.add_argument("invocation", help="Invocation string, e.g. '/orchestrator @default_fallback_profile'")
    p_init.add_argument("--status-file", default=str(DEFAULT_STATUS))
    p_init.add_argument("--charter-version", default="v2.0")
    p_init.add_argument("--idea-id", default="")
    p_init.add_argument("--idea-headline", default=None)
    p_init.set_defaults(func=cmd_init)

    p_vs = sub.add_parser("validate-status", help="Validate status.json against schema")
    p_vs.add_argument("--status-file", default=str(DEFAULT_STATUS))
    p_vs.set_defaults(func=cmd_validate_status)

    p_gate = sub.add_parser("set-gate", help="Set governance gate decision")
    p_gate.add_argument("gate_id")
    p_gate.add_argument("decision", choices=["pending", "approved", "rejected"])
    p_gate.add_argument("--reason", default="")
    p_gate.add_argument("--status-file", default=str(DEFAULT_STATUS))
    p_gate.set_defaults(func=cmd_set_gate)

    p_step = sub.add_parser("step", help="Advance one deterministic step")
    p_step.add_argument("--status-file", default=str(DEFAULT_STATUS))
    p_step.add_argument("--trace-file", default="")
    p_step.set_defaults(func=cmd_step)

    p_run = sub.add_parser("run", help="Autonomously run workflow until done or human gate")
    p_run.add_argument("--status-file", default=str(DEFAULT_STATUS))
    p_run.add_argument("--trace-file", default="")
    p_run.add_argument("--max-steps", type=int, default=200)
    p_run.set_defaults(func=cmd_run)

    p_trigger = sub.add_parser(
        "trigger",
        help="Agent-style trigger: resolve active idea from context.md then init+run",
    )
    p_trigger.add_argument("command", help="Trigger command, e.g. '/orchestrator' or '/orchestrator @profile'")
    p_trigger.add_argument("--status-file", default=str(DEFAULT_STATUS))
    p_trigger.add_argument("--charter-version", default="v2.2")
    p_trigger.add_argument("--max-steps", type=int, default=400)
    p_trigger.add_argument("--trace-file", default="")
    p_trigger.add_argument("--context-file", default=str(DEFAULT_CONTEXT))
    p_trigger.add_argument("--ideas-dir", default=str(DEFAULT_IDEAS_DIR))
    p_trigger.set_defaults(func=cmd_trigger)

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except OrchestratorV2Error as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
