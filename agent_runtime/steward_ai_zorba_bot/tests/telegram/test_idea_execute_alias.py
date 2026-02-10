#!/usr/bin/env python3
"""Tests for /idea command routing aliases."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.telegram import idea_chat as idea_chat_module


async def _noop_send(_user_id: int, _text: str) -> None:
    return None


def test_execute_command_routes_to_execute(monkeypatch):
    monkeypatch.setattr(idea_chat_module, "restore_active_sessions", lambda: {})
    chat = idea_chat_module.IdeaChat(send_func=_noop_send)

    called = {}

    async def fake_execute(user_id: int, idea_id: str):
        called["user_id"] = user_id
        called["idea_id"] = idea_id

    chat.execute = fake_execute  # type: ignore[method-assign]

    handled = asyncio.run(chat.handle_command(7, "/idea execute my_idea_id"))

    assert handled is True
    assert called == {"user_id": 7, "idea_id": "my_idea_id"}


def test_activate_command_routes_to_activate(monkeypatch):
    monkeypatch.setattr(idea_chat_module, "restore_active_sessions", lambda: {})
    chat = idea_chat_module.IdeaChat(send_func=_noop_send)

    called = {}

    async def fake_activate(user_id: int, idea_id: str):
        called["user_id"] = user_id
        called["idea_id"] = idea_id

    chat.activate = fake_activate  # type: ignore[method-assign]

    handled = asyncio.run(chat.handle_command(9, "/idea activate another_id"))

    assert handled is True
    assert called == {"user_id": 9, "idea_id": "another_id"}


def test_activate_command_with_bot_mention_routes_to_activate(monkeypatch):
    monkeypatch.setattr(idea_chat_module, "restore_active_sessions", lambda: {})
    chat = idea_chat_module.IdeaChat(send_func=_noop_send)

    called = {}

    async def fake_activate(user_id: int, idea_id: str):
        called["user_id"] = user_id
        called["idea_id"] = idea_id

    chat.activate = fake_activate  # type: ignore[method-assign]

    handled = asyncio.run(chat.handle_command(9, "/idea@my_bot activate another_id"))

    assert handled is True
    assert called == {"user_id": 9, "idea_id": "another_id"}


def test_active_alias_routes_to_activate(monkeypatch):
    monkeypatch.setattr(idea_chat_module, "restore_active_sessions", lambda: {})
    chat = idea_chat_module.IdeaChat(send_func=_noop_send)

    called = {}

    async def fake_activate(user_id: int, idea_id: str):
        called["user_id"] = user_id
        called["idea_id"] = idea_id

    chat.activate = fake_activate  # type: ignore[method-assign]

    handled = asyncio.run(chat.handle_command(12, "/idea active sample_alias_id"))

    assert handled is True
    assert called == {"user_id": 12, "idea_id": "sample_alias_id"}


def test_continue_alias_routes_to_start_existing(monkeypatch):
    monkeypatch.setattr(idea_chat_module, "restore_active_sessions", lambda: {})
    chat = idea_chat_module.IdeaChat(send_func=_noop_send)

    called = {}

    async def fake_start_existing(user_id: int, idea_id: str):
        called["user_id"] = user_id
        called["idea_id"] = idea_id

    chat.start_existing_session = fake_start_existing  # type: ignore[method-assign]

    handled = asyncio.run(chat.handle_command(5, "/idea continue sample_id"))

    assert handled is True
    assert called == {"user_id": 5, "idea_id": "sample_id"}


def test_start_command_routes_to_start_existing(monkeypatch):
    monkeypatch.setattr(idea_chat_module, "restore_active_sessions", lambda: {})
    chat = idea_chat_module.IdeaChat(send_func=_noop_send)

    called = {}

    async def fake_start_existing(user_id: int, idea_id: str):
        called["user_id"] = user_id
        called["idea_id"] = idea_id

    chat.start_existing_session = fake_start_existing  # type: ignore[method-assign]

    handled = asyncio.run(chat.handle_command(6, "/idea start focused_tab_categorizer"))

    assert handled is True
    assert called == {"user_id": 6, "idea_id": "focused_tab_categorizer"}
