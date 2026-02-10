#!/usr/bin/env python3
"""Tests for gate-specific answer handling in question poller."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.telegram.question_poller import QuestionPoller


async def _noop_send(_user_id: int, _text: str) -> None:
    return None


def test_process_answer_gate_requires_clarification(monkeypatch):
    monkeypatch.setattr(
        "apps.telegram.question_poller.get_delivered_questions",
        lambda: [{"id": "Q-GATE-RELEASE_APPROVAL-1", "delivery_status": "delivered"}],
    )
    monkeypatch.setattr(
        "apps.telegram.question_poller.handle_gate_answer",
        lambda _qid, _answer, source="telegram": {
            "handled": True,
            "accepted": False,
            "message": "Please reply with approve/reject.",
            "decision": None,
        },
    )

    poller = QuestionPoller(send_func=_noop_send, user_ids=[1])
    answered = poller.process_answer("maybe")

    assert answered is None
    assert poller.last_needs_clarification is True
    assert "approve" in poller.last_feedback.lower()
    assert poller.current_question_id == "Q-GATE-RELEASE_APPROVAL-1"


def test_process_answer_gate_accepted(monkeypatch):
    monkeypatch.setattr(
        "apps.telegram.question_poller.get_delivered_questions",
        lambda: [{"id": "Q-GATE-RELEASE_APPROVAL-1", "delivery_status": "delivered"}],
    )
    monkeypatch.setattr(
        "apps.telegram.question_poller.handle_gate_answer",
        lambda _qid, _answer, source="telegram": {
            "handled": True,
            "accepted": True,
            "message": "Approval accepted. Workflow resumed.",
            "decision": "approved",
        },
    )

    poller = QuestionPoller(send_func=_noop_send, user_ids=[1])
    answered = poller.process_answer("1")

    assert answered == "Q-GATE-RELEASE_APPROVAL-1"
    assert poller.last_needs_clarification is False
    assert "workflow resumed" in poller.last_feedback.lower()
    assert poller.current_question_id is None


def test_poll_once_sends_completion_notification_once(monkeypatch):
    sent = []

    async def _capture_send(_user_id: int, text: str) -> None:
        sent.append(text)

    monkeypatch.setattr("apps.telegram.question_poller.get_delivered_questions", lambda: [])
    monkeypatch.setattr("apps.telegram.question_poller.get_pending_questions", lambda: [])
    monkeypatch.setattr(
        "apps.telegram.question_poller.read_status",
        lambda: {
            "active_run_id": "run-smartbookmarker-1",
            "active_idea_id": "smartbookmarker_ai_powered_boo",
            "active_idea_headline": "SmartBookmarker: AI-Powered Bookmark Organizer",
            "current_phase": "done",
            "realization_status": "completed",
            "artifacts": {"a.md": {"path": "x"}},
        },
    )

    poller = QuestionPoller(send_func=_capture_send, user_ids=[1])
    first = asyncio.run(poller.poll_once())
    second = asyncio.run(poller.poll_once())

    assert first is True
    assert second is False
    assert len(sent) == 1
    assert "Workflow completed" in sent[0]
    assert "smartbookmarker_ai_powered_boo" in sent[0]
