#!/usr/bin/env python3
"""Tests for /idea activate and /idea execute flow."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.telegram import idea_chat as idea_chat_module


def test_execute_requires_activation(monkeypatch):
    sent = []

    async def fake_send(_user_id: int, text: str):
        sent.append(text)

    monkeypatch.setattr(idea_chat_module, "restore_active_sessions", lambda: {})
    monkeypatch.setattr(
        idea_chat_module,
        "execute_idea",
        lambda _idea_id, owner_user_id=None: (
            False,
            "Idea context must be active before execute. Run `/idea activate idea1` first.",
        ),
    )

    chat = idea_chat_module.IdeaChat(send_func=fake_send)
    asyncio.run(chat.execute(1, "idea1"))

    assert any("activate" in msg.lower() for msg in sent)


def test_execute_calls_orchestrator_for_planned_idea(monkeypatch):
    sent = []

    async def fake_send(_user_id: int, text: str):
        sent.append(text)

    monkeypatch.setattr(idea_chat_module, "restore_active_sessions", lambda: {})
    monkeypatch.setattr(
        idea_chat_module,
        "execute_idea",
        lambda _idea_id, owner_user_id=None: (True, "Initialized flow: profile=default_fallback_profile step=0"),
    )

    chat = idea_chat_module.IdeaChat(send_func=fake_send)
    asyncio.run(chat.execute(1, "idea2"))

    assert any("Execution" in msg for msg in sent)
    assert any("Initialized flow" in msg for msg in sent)


def test_activate_copies_context(monkeypatch):
    sent = []

    async def fake_send(_user_id: int, text: str):
        sent.append(text)

    monkeypatch.setattr(idea_chat_module, "restore_active_sessions", lambda: {})
    monkeypatch.setattr(
        idea_chat_module,
        "activate_idea",
        lambda _idea_id, owner_user_id=None: (True, "Activated context for idea: SmartBookmarker"),
    )

    chat = idea_chat_module.IdeaChat(send_func=fake_send)
    asyncio.run(chat.activate(1, "smartbookmarker"))

    assert any("Activated context" in msg for msg in sent)
    assert any("execute" in msg.lower() for msg in sent)


def test_stop_session_closes_as_refined(monkeypatch):
    sent = []

    async def fake_send(_user_id: int, text: str):
        sent.append(text)

    monkeypatch.setattr(idea_chat_module, "restore_active_sessions", lambda: {})
    monkeypatch.setattr(idea_chat_module, "get_active_idea", lambda _user_id: "idea_raw")
    monkeypatch.setattr(
        idea_chat_module,
        "get_chat_history",
        lambda _idea_id: [{"role": "user", "content": "idea details"}],
    )
    monkeypatch.setattr(idea_chat_module, "end_idea", lambda _user_id: "idea_raw")

    chat = idea_chat_module.IdeaChat(send_func=fake_send)
    asyncio.run(chat.stop_session(1))

    assert any("REFINED" in msg for msg in sent)
    assert any("good day" in msg.lower() for msg in sent)
