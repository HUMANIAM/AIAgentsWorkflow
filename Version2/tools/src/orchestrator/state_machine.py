#!/usr/bin/env python3
"""State machine logic for profile-driven orchestration."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from orchestrator import utils as orch_utils


@dataclass
class StepResult:
    changed: bool
    outcome: str
    message: str


def compile_phase_plan(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    plan: List[Dict[str, Any]] = []
    idx = 0
    for phase in profile.get("phases", []):
        phase_id = phase["id"]
        for role_step in phase.get("roles", []):
            step: Dict[str, Any] = {
                "index": idx,
                "phase": phase_id,
                "role": role_step["role"],
                "step_id": role_step["id"],
                "step_type": role_step["step_type"],
                "required_outputs": list(role_step.get("required_outputs", [])),
            }
            if "review_of" in role_step:
                step["review_of"] = role_step["review_of"]
            if "gate" in role_step:
                step["gate"] = role_step["gate"]
            if "notes" in role_step:
                step["notes"] = role_step["notes"]
            plan.append(step)
            idx += 1
    return plan


def gate_map(status: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    mapped: Dict[str, Dict[str, Any]] = {}
    for gate in status.get("governance_gates", []):
        if isinstance(gate, dict) and isinstance(gate.get("id"), str):
            mapped[gate["id"]] = gate
    return mapped


def setup_from_profile(
    status: Dict[str, Any],
    profile: Dict[str, Any],
    profile_name: str,
    charter_version: str,
    *,
    now_fn: Callable[[], str] = orch_utils.utc_now,
    error_cls: type[Exception] = RuntimeError,
) -> Dict[str, Any]:
    plan = compile_phase_plan(profile)
    if not plan:
        raise error_cls("Profile produced an empty phase plan.")

    execution_mode = str(profile.get("execution_mode", "simulation")).strip().lower()
    if execution_mode not in {"simulation", "realization"}:
        raise error_cls(f"Unsupported execution_mode in profile: {execution_mode}")

    gates = []
    for gate in profile.get("gates", []):
        gates.append(
            {
                "id": gate["id"],
                "status": "pending",
                "owner": gate["owner"],
                "reason": "",
                "updated_at": now_fn(),
            }
        )

    now = now_fn()
    step0 = plan[0]
    next_status: Dict[str, Any] = {
        "active_profile": profile_name,
        "phase_plan": plan,
        "current_step_index": 0,
        "current_phase": step0["phase"],
        "current_role": step0["role"],
        "phase_status": "in_progress",
        "role_status": "not_started",
        "review_status": "not_started",
        "realization_status": "executing",
        "pending_human_gate_id": "",
        "pending_human_question_id": "",
        "execution_mode": execution_mode,
        "workspace_dir": str(status.get("workspace_dir", "")),
        "workspace_git_initialized": bool(status.get("workspace_git_initialized", False)),
        "active_run_id": f"run-{profile_name}-{now.replace(':', '').replace('-', '')}",
        "last_failed_role": "",
        "integration_loop_status": "idle",
        "commit_evidence": list(status.get("commit_evidence", [])),
        "role_attempts": dict(status.get("role_attempts", {})),
        "questions": list(status.get("questions", [])),
        "answers": list(status.get("answers", [])),
        "governance_gates": gates,
        "review_cycles": {},
        "blocking_reasons": [],
        "handoff_packet": {
            "required_outputs": step0.get("required_outputs", []),
            "provided_outputs": [],
            "missing_outputs": [],
            "from_step": "",
            "to_step": step0["step_id"],
            "updated_at": now,
        },
        "artifacts": dict(status.get("artifacts", {})),
        "evidence": list(status.get("evidence", [])),
        "critical_failures": list(status.get("critical_failures", [])),
        "charter_version": charter_version,
        "score_run_id": f"score-{profile_name}-{now.replace(':', '').replace('-', '')}",
        "timestamps": {
            "workflow_started_at": now,
            "last_transition_at": now,
        },
    }

    for key in ["active_idea_id", "active_idea_headline", "active_idea"]:
        if key in status:
            next_status[key] = deepcopy(status[key])
    return next_status


def find_missing_outputs(status: Dict[str, Any], step: Dict[str, Any]) -> List[str]:
    artifacts = status.get("artifacts", {})
    missing: List[str] = []

    def has_output(name: str) -> bool:
        for key, meta in artifacts.items():
            if key == name:
                return True
            if isinstance(meta, dict):
                path = meta.get("path")
                if isinstance(path, str) and path.endswith(name):
                    return True
        return False

    for item in step.get("required_outputs", []):
        if not has_output(item):
            missing.append(item)
    return missing


def unresolved_required_questions(status: Dict[str, Any]) -> List[str]:
    answer_ids = {a.get("question_id") for a in status.get("answers", []) if isinstance(a, dict)}
    unresolved: List[str] = []
    for q in status.get("questions", []):
        if not isinstance(q, dict):
            continue
        if not q.get("required", False):
            continue
        qid = q.get("id")
        qstate = q.get("status")
        if qstate in {"answered", "closed"} and qid in answer_ids:
            continue
        if isinstance(qid, str):
            unresolved.append(qid)
    return unresolved


def unresolved_critical_failures(status: Dict[str, Any]) -> List[str]:
    failures: List[str] = []
    for item in status.get("critical_failures", []):
        if isinstance(item, dict) and item.get("status") == "open":
            failures.append(str(item.get("id", "critical_failure")))
    return failures


def get_current_step(
    status: Dict[str, Any],
    *,
    error_cls: type[Exception] = RuntimeError,
) -> Dict[str, Any]:
    plan = status.get("phase_plan", [])
    idx = status.get("current_step_index", 0)
    if not isinstance(plan, list) or not isinstance(idx, int):
        raise error_cls("Invalid phase_plan or current_step_index in status.")
    if idx < 0 or idx >= len(plan):
        raise error_cls("current_step_index is out of bounds.")
    step = plan[idx]
    if not isinstance(step, dict):
        raise error_cls("Current step is not an object.")
    return step


def profile_max_review_cycles(profile: Dict[str, Any]) -> int:
    defaults = profile.get("defaults", {})
    if isinstance(defaults, dict):
        value = defaults.get("max_review_cycles")
        if isinstance(value, int) and value > 0:
            return value
    return 2


def _find_role_step_index_before(plan: List[Dict[str, Any]], current_idx: int, role: str) -> Optional[int]:
    for idx in range(current_idx - 1, -1, -1):
        step = plan[idx]
        if step.get("role") == role:
            return idx
    return None


def producer_index_for_reviewer(
    status: Dict[str, Any],
    reviewer_step: Dict[str, Any],
    *,
    error_cls: type[Exception] = RuntimeError,
) -> int:
    plan = status["phase_plan"]
    current_idx = int(reviewer_step["index"])
    phase = str(reviewer_step["phase"])
    review_of = reviewer_step.get("review_of")

    if reviewer_step.get("role") == "integration_tester":
        target = str(status.get("integration_failure_target", "")).strip() or "backend_engineer"
        routed = _find_role_step_index_before(plan, current_idx, target)
        if routed is not None:
            return routed

    for idx in range(current_idx - 1, -1, -1):
        candidate = plan[idx]
        if candidate.get("phase") != phase:
            break
        if review_of and candidate.get("role") == review_of:
            return idx

    for idx in range(current_idx - 1, -1, -1):
        candidate = plan[idx]
        if candidate.get("phase") != phase:
            break
        if candidate.get("step_type") in {"owner", "validator"}:
            return idx

    raise error_cls(f"Could not find producer step for reviewer {reviewer_step.get('step_id')}.")


def move_to_step(
    status: Dict[str, Any],
    target_idx: int,
    from_step_id: str,
    *,
    now_fn: Callable[[], str] = orch_utils.utc_now,
) -> None:
    plan = status["phase_plan"]
    if target_idx >= len(plan):
        status["current_step_index"] = len(plan)
        status["current_phase"] = "done"
        status["current_role"] = "orchestrator"
        status["phase_status"] = "completed"
        status["role_status"] = "completed"
        status["review_status"] = "approved"
        if status.get("realization_status") != "rejected":
            status["realization_status"] = "completed"
        status["pending_human_gate_id"] = ""
        status["pending_human_question_id"] = ""
        status["blocking_reasons"] = []
        if str(status.get("execution_mode", "simulation")) == "realization":
            status["integration_loop_status"] = "passed"
        status["handoff_packet"] = {
            "required_outputs": [],
            "provided_outputs": [],
            "missing_outputs": [],
            "from_step": from_step_id,
            "to_step": "done",
            "updated_at": now_fn(),
        }
        status["timestamps"]["last_transition_at"] = now_fn()
        return

    next_step = plan[target_idx]
    status["current_step_index"] = target_idx
    status["current_phase"] = next_step["phase"]
    status["current_role"] = next_step["role"]
    status["phase_status"] = "in_progress"
    status["role_status"] = "not_started"
    status["review_status"] = "in_review" if next_step.get("step_type") == "reviewer" else "not_started"
    status["pending_human_gate_id"] = ""
    status["blocking_reasons"] = []
    status["handoff_packet"] = {
        "required_outputs": list(next_step.get("required_outputs", [])),
        "provided_outputs": [],
        "missing_outputs": [],
        "from_step": from_step_id,
        "to_step": next_step.get("step_id", ""),
        "updated_at": now_fn(),
    }
    status["timestamps"]["last_transition_at"] = now_fn()


def compute_blocking(status: Dict[str, Any], step: Dict[str, Any]) -> List[str]:
    reasons: List[str] = []

    unresolved_questions = unresolved_required_questions(status)
    if unresolved_questions:
        reasons.append("Required client questions unresolved: " + ", ".join(sorted(unresolved_questions)))

    unresolved_failures = unresolved_critical_failures(status)
    if unresolved_failures:
        reasons.append("Critical failures unresolved: " + ", ".join(sorted(unresolved_failures)))

    gate_id = step.get("gate")
    if isinstance(gate_id, str):
        gates = gate_map(status)
        gate = gates.get(gate_id)
        if not gate:
            reasons.append(f"Missing required governance gate: {gate_id}")
        else:
            state = gate.get("status")
            if state == "pending":
                reasons.append(f"Awaiting human approval for gate: {gate_id}")
            elif state == "rejected":
                reasons.append(f"Gate rejected by human: {gate_id}")

    return reasons


def step_once(
    status: Dict[str, Any],
    profile: Dict[str, Any],
    *,
    now_fn: Callable[[], str] = orch_utils.utc_now,
    error_cls: type[Exception] = RuntimeError,
) -> StepResult:
    step = get_current_step(status, error_cls=error_cls)

    if status.get("current_phase") != step.get("phase") or status.get("current_role") != step.get("role"):
        raise error_cls(
            "Illegal transition state: current cursor does not match compiled phase plan step."
        )

    blocking = compute_blocking(status, step)
    if blocking:
        status["blocking_reasons"] = blocking
        status["phase_status"] = "waiting"
        return StepResult(False, "blocked", " ; ".join(blocking))

    status["blocking_reasons"] = []
    step_type = step.get("step_type")

    if step_type == "gate":
        gate_id = step.get("gate")
        gate = gate_map(status).get(gate_id)
        if not gate:
            raise error_cls(f"Missing gate definition in status for {gate_id}.")
        if gate.get("status") == "approved":
            move_to_step(status, int(step["index"]) + 1, str(step.get("step_id", "")), now_fn=now_fn)
            return StepResult(True, "advanced", f"Gate {gate_id} approved; advanced.")
        status["phase_status"] = "waiting"
        return StepResult(False, "waiting", f"Gate {gate_id} is not approved yet.")

    if step_type in {"owner", "validator"}:
        if status.get("role_status") != "completed":
            return StepResult(False, "waiting", "Current role has not marked work completed.")
        missing = find_missing_outputs(status, step)
        if missing:
            status.setdefault("handoff_packet", {})["missing_outputs"] = missing
            raise error_cls(
                "Missing required outputs for step "
                f"{step.get('step_id')}: {', '.join(missing)}"
            )
        move_to_step(status, int(step["index"]) + 1, str(step.get("step_id", "")), now_fn=now_fn)
        return StepResult(True, "advanced", "Role complete with required outputs.")

    if step_type == "reviewer":
        if status.get("role_status") != "completed":
            return StepResult(False, "waiting", "Reviewer has not marked review completed.")

        verdict = status.get("review_status")
        if verdict == "changes_requested":
            if step.get("role") == "integration_tester":
                attempts = int(status.get("role_attempts", {}).get("integration_tester", 0))
                if attempts >= 3:
                    status["phase_status"] = "blocked"
                    status["blocking_reasons"] = [
                        "Integration retry cap exceeded (3). Human escalation required."
                    ]
                    status["integration_loop_status"] = "failed"
                    return StepResult(False, "blocked", status["blocking_reasons"][0])

                target = str(status.get("integration_failure_target", "backend_engineer"))
                producer_idx = producer_index_for_reviewer(status, step, error_cls=error_cls)
                status["last_failed_role"] = target
                move_to_step(status, producer_idx, str(step.get("step_id", "")), now_fn=now_fn)
                return StepResult(
                    True,
                    "rerouted",
                    f"Integration test failed; rerouted to {target}.",
                )

            phase = str(step.get("phase"))
            cycles = int(status.get("review_cycles", {}).get(phase, 0)) + 1
            status["review_cycles"][phase] = cycles
            max_cycles = profile_max_review_cycles(profile)

            if cycles > max_cycles:
                status["phase_status"] = "blocked"
                status["blocking_reasons"] = [
                    f"Review cycle cap exceeded for phase '{phase}'. Human decision required."
                ]
                return StepResult(False, "blocked", status["blocking_reasons"][0])

            producer_idx = producer_index_for_reviewer(status, step, error_cls=error_cls)
            move_to_step(status, producer_idx, str(step.get("step_id", "")), now_fn=now_fn)
            return StepResult(True, "rerouted", "Reviewer requested changes; rerouted to producer.")

        if verdict != "approved":
            return StepResult(False, "waiting", "Reviewer verdict must be approved or changes_requested.")

        missing = find_missing_outputs(status, step)
        if missing:
            status.setdefault("handoff_packet", {})["missing_outputs"] = missing
            raise error_cls(
                f"Missing required reviewer outputs for {step.get('step_id')}: {', '.join(missing)}"
            )

        move_to_step(status, int(step["index"]) + 1, str(step.get("step_id", "")), now_fn=now_fn)
        return StepResult(True, "advanced", "Reviewer approved; advanced to next step.")

    raise error_cls(f"Unsupported step_type: {step_type}")
