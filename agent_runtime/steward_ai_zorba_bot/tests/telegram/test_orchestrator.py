#!/usr/bin/env python3
"""Unit tests for orchestrator workflow helpers."""

import unittest
import importlib.util
import sys
from pathlib import Path


ORCHESTRATOR_PATH = Path(__file__).resolve().parents[2] / "orchestrator.py"
SPEC = importlib.util.spec_from_file_location("legacy_orchestrator_under_test", ORCHESTRATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Failed to load legacy orchestrator module from {ORCHESTRATOR_PATH}")
orchestrator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = orchestrator
SPEC.loader.exec_module(orchestrator)


def _base_status(**overrides):
    status = {
        "problem": {},
        "cycle": 0,
        "current_phase": "bootstrap_comms",
        "current_actor": "devops",
        "phase_status": "in_progress",
        "actor_status": "not_started",
        "review_status": "not_started",
        "comms": {"state": "ready"},
        "client_action_required": False,
        "client_channel": {},
        "client_questions": [],
        "client_answers": [],
        "ack_requests": [],
        "changesets": {},
        "artifacts": {},
        "gates": {
            "COMMS_READY": "pending",
            "REQ_REVIEW_APPROVED": "pending",
            "REQ_CLIENT_ACK": "pending",
            "ARCH_REVIEW_APPROVED": "pending",
            "DEVOPS_REVIEW_APPROVED": "pending",
            "SECURITY_APPROVED": "pending",
            "FINAL_CLIENT_ACK": "pending",
        },
        "timestamps": {},
    }
    status.update(overrides)
    return status


class TestOrchestratorTransitions(unittest.TestCase):
    def test_kickoff_when_phase_invalid(self):
        status = _base_status(current_phase="bogus", current_actor="nobody")
        patch = orchestrator.compute_next_transition(status)
        self.assertIsNotNone(patch)
        self.assertEqual(patch["current_phase"], "bootstrap_comms")
        self.assertEqual(patch["current_actor"], "devops")

    def test_owner_completed_triggers_reviewer(self):
        status = _base_status(
            current_phase="requirements",
            current_actor="system_analyst",
            phase_status="in_progress",
            actor_status="completed",
            review_status="not_started",
        )
        patch = orchestrator.compute_next_transition(status)
        self.assertEqual(patch["current_actor"], "system_analyst_reviewer")
        self.assertEqual(patch["phase_status"], "awaiting_review")
        self.assertEqual(patch["review_status"], "in_review")

    def test_reviewer_approved_advances_phase(self):
        status = _base_status(
            current_phase="requirements",
            current_actor="system_analyst_reviewer",
            phase_status="awaiting_review",
            actor_status="completed",
            review_status="approved",
        )
        patch = orchestrator.compute_next_transition(status)
        self.assertEqual(patch["current_phase"], "architecture")
        self.assertEqual(patch["current_actor"], "architect")

    def test_reviewer_changes_requested_returns_to_owner(self):
        status = _base_status(
            current_phase="requirements",
            current_actor="system_analyst_reviewer",
            phase_status="awaiting_review",
            actor_status="completed",
            review_status="changes_requested",
        )
        patch = orchestrator.compute_next_transition(status)
        self.assertEqual(patch["current_actor"], "system_analyst")
        self.assertEqual(patch["phase_status"], "in_progress")

    def test_waiting_on_owner_no_transition(self):
        status = _base_status(
            current_phase="requirements",
            current_actor="system_analyst",
            phase_status="in_progress",
            actor_status="in_progress",
        )
        patch = orchestrator.compute_next_transition(status)
        self.assertIsNone(patch)


class TestOrchestratorReconcile(unittest.TestCase):
    def test_reconcile_sets_comms_gate(self):
        status = _base_status(comms={"state": "ready"}, gates={"COMMS_READY": "pending"})
        changed = orchestrator.reconcile_gates(status)
        self.assertTrue(changed)
        self.assertEqual(status["gates"]["COMMS_READY"], "pass")

    def test_reconcile_sets_requirements_gates_from_ack(self):
        status = _base_status(
            gates={"REQ_REVIEW_APPROVED": "pending", "REQ_CLIENT_ACK": "pending"},
            ack_requests=[{"type": "requirements_review", "status": "approved"}],
        )
        changed = orchestrator.reconcile_gates(status)
        self.assertTrue(changed)
        self.assertEqual(status["gates"]["REQ_REVIEW_APPROVED"], "pass")
        self.assertEqual(status["gates"]["REQ_CLIENT_ACK"], "pass")


if __name__ == "__main__":
    unittest.main()
