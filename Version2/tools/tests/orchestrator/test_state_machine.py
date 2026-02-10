#!/usr/bin/env python3
"""Unit tests for orchestrator state machine module."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from orchestrator import state_machine


def test_setup_from_profile_rejects_invalid_execution_mode():
    profile = {
        "execution_mode": "invalid_mode",
        "gates": [],
        "phases": [
            {
                "id": "requirements",
                "roles": [
                    {
                        "id": "requirements_owner",
                        "role": "system_analyst",
                        "step_type": "owner",
                        "required_outputs": ["acceptance_contract.md"],
                    }
                ],
            }
        ],
    }
    with pytest.raises(RuntimeError):
        state_machine.setup_from_profile(
            status={},
            profile=profile,
            profile_name="sample",
            charter_version="test",
            error_cls=RuntimeError,
        )


def test_find_missing_outputs_accepts_path_basename_match():
    status = {
        "artifacts": {
            "any_key": {
                "path": "/tmp/reports/review_requirements.md",
                "owner": "requirements_reviewer",
            }
        }
    }
    step = {"required_outputs": ["review_requirements.md"]}
    assert state_machine.find_missing_outputs(status, step) == []


def test_step_once_blocks_on_pending_gate():
    status = {
        "phase_plan": [
            {
                "index": 0,
                "phase": "requirements",
                "role": "human_engineer",
                "step_id": "requirements_gate",
                "step_type": "gate",
                "gate": "REQ_FREEZE_APPROVAL",
                "required_outputs": [],
            }
        ],
        "current_step_index": 0,
        "current_phase": "requirements",
        "current_role": "human_engineer",
        "role_status": "in_progress",
        "questions": [],
        "answers": [],
        "critical_failures": [],
        "governance_gates": [
            {
                "id": "REQ_FREEZE_APPROVAL",
                "status": "pending",
                "owner": "human_engineer",
            }
        ],
    }
    profile = {"defaults": {"max_review_cycles": 2}}
    result = state_machine.step_once(status, profile, error_cls=RuntimeError)
    assert result.outcome == "blocked"
    assert "Awaiting human approval for gate: REQ_FREEZE_APPROVAL" in status["blocking_reasons"][0]
