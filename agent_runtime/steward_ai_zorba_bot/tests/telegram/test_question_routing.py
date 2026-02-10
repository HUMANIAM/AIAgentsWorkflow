#!/usr/bin/env python3
"""Tests for question routing and delivered-question recovery."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.telegram.question_poller import QuestionPoller
from apps.telegram import app as telegram_app


async def _noop_send(_user_id: int, _text: str) -> None:
    return None


def test_process_answer_recovers_delivered_question(monkeypatch):
    writes = []

    monkeypatch.setattr(
        "apps.telegram.question_poller.get_delivered_questions",
        lambda: [{"id": "Q-RECOVER-1", "delivery_status": "delivered"}],
    )
    monkeypatch.setattr(
        "apps.telegram.question_poller.write_answer",
        lambda question_id, answer, source="telegram": writes.append((question_id, answer, source)),
    )

    poller = QuestionPoller(send_func=_noop_send, user_ids=[1])
    answered_id = poller.process_answer("  hello  ")

    assert answered_id == "Q-RECOVER-1"
    assert writes == [("Q-RECOVER-1", "hello", "telegram")]
    assert poller.current_question_id is None


def test_poll_once_does_not_deliver_new_when_delivered_exists(monkeypatch):
    delivered_calls = {"count": 0}

    monkeypatch.setattr(
        "apps.telegram.question_poller.get_delivered_questions",
        lambda: [{"id": "Q-DELIVERED-1", "delivery_status": "delivered"}],
    )
    monkeypatch.setattr(
        "apps.telegram.question_poller.get_pending_questions",
        lambda: [{"id": "Q-PENDING-1", "question": "Should not send this yet"}],
    )

    poller = QuestionPoller(send_func=_noop_send, user_ids=[1])

    async def fake_deliver_question(_question):
        delivered_calls["count"] += 1
        return True

    poller.deliver_question = fake_deliver_question  # type: ignore[method-assign]
    sent = asyncio.run(poller.poll_once())

    assert sent is False
    assert delivered_calls["count"] == 0
    assert poller.current_question_id == "Q-DELIVERED-1"


def test_handle_message_prioritizes_active_idea_text(monkeypatch):
    class DummyConfig:
        def is_allowed(self, _user_id: int) -> bool:
            return True

        def real_users(self):
            return [1]

    class DummyPoller:
        def __init__(self):
            self.calls = []

        def has_open_question(self):
            return True

        def process_answer(self, text: str):
            self.calls.append(text)
            return "Q-PRIORITY-1"

    class DummyIdeaChat:
        def __init__(self):
            self.calls = []

        async def process_message(self, user_id: int, text: str):
            self.calls.append((user_id, text))

    replies = []

    async def fake_reply(_update, text: str):
        replies.append(text)

    monkeypatch.setattr(telegram_app, "Config", DummyConfig)
    monkeypatch.setattr(telegram_app, "get_user_id", lambda _update: 1)
    monkeypatch.setattr(telegram_app, "get_text", lambda _update: "long brainstorming message")
    monkeypatch.setattr(telegram_app, "reply", fake_reply)

    import services.idea_handler as idea_handler

    monkeypatch.setattr(idea_handler, "get_active_idea", lambda _user_id: "IDEA-1")

    bot = telegram_app.TelegramBot()
    bot.question_poller = DummyPoller()
    bot.idea_chat = DummyIdeaChat()

    asyncio.run(bot.handle_message(object(), None))

    assert bot.question_poller.calls == []
    assert bot.idea_chat.calls == [(1, "long brainstorming message")]
    assert replies == []


def test_handle_message_accepts_numeric_answer_during_active_idea(monkeypatch):
    class DummyConfig:
        def is_allowed(self, _user_id: int) -> bool:
            return True

        def real_users(self):
            return [1]

    class DummyPoller:
        def __init__(self):
            self.calls = []

        def has_open_question(self):
            return True

        def process_answer(self, text: str):
            self.calls.append(text)
            return "Q-ACTIVE-1"

    class DummyIdeaChat:
        def __init__(self):
            self.calls = []

        async def process_message(self, user_id: int, text: str):
            self.calls.append((user_id, text))

    replies = []

    async def fake_reply(_update, text: str):
        replies.append(text)

    monkeypatch.setattr(telegram_app, "Config", DummyConfig)
    monkeypatch.setattr(telegram_app, "get_user_id", lambda _update: 1)
    monkeypatch.setattr(telegram_app, "get_text", lambda _update: "2")
    monkeypatch.setattr(telegram_app, "reply", fake_reply)

    import services.idea_handler as idea_handler

    monkeypatch.setattr(idea_handler, "get_active_idea", lambda _user_id: "IDEA-1")

    bot = telegram_app.TelegramBot()
    bot.question_poller = DummyPoller()
    bot.idea_chat = DummyIdeaChat()

    asyncio.run(bot.handle_message(object(), None))

    assert bot.question_poller.calls == ["2"]
    assert bot.idea_chat.calls == []
    assert any("Team question answered" in message for message in replies)


def test_handle_message_routes_command_like_text_to_idea_command(monkeypatch):
    class DummyConfig:
        def is_allowed(self, _user_id: int) -> bool:
            return True

        def real_users(self):
            return [1]

    class DummyPoller:
        def __init__(self):
            self.calls = []

        def has_open_question(self):
            return True

        def process_answer(self, text: str):
            self.calls.append(text)
            return "Q-CMD-1"

    class DummyIdeaChat:
        def __init__(self):
            self.command_calls = []
            self.message_calls = []

        async def handle_command(self, user_id: int, text: str):
            self.command_calls.append((user_id, text))
            return True

        async def process_message(self, user_id: int, text: str):
            self.message_calls.append((user_id, text))

    replies = []

    async def fake_reply(_update, text: str):
        replies.append(text)

    monkeypatch.setattr(telegram_app, "Config", DummyConfig)
    monkeypatch.setattr(telegram_app, "get_user_id", lambda _update: 1)
    monkeypatch.setattr(telegram_app, "get_text", lambda _update: "/idea activate smartbookmarker_ai_powered_boo")
    monkeypatch.setattr(telegram_app, "reply", fake_reply)

    import services.idea_handler as idea_handler

    monkeypatch.setattr(idea_handler, "get_active_idea", lambda _user_id: "IDEA-1")

    bot = telegram_app.TelegramBot()
    bot.question_poller = DummyPoller()
    bot.idea_chat = DummyIdeaChat()

    asyncio.run(bot.handle_message(object(), None))

    assert bot.idea_chat.command_calls == [(1, "/idea activate smartbookmarker_ai_powered_boo")]
    assert bot.idea_chat.message_calls == []
    assert bot.question_poller.calls == []
    assert replies == []
