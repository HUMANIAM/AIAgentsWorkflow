#!/usr/bin/env python3
"""Tests for idea headline generation robustness."""

from types import SimpleNamespace
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services import openai_client


class _FakeClient:
    def __init__(self, content: str):
        self._content = content
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )

    def _create(self, **_kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._content))]
        )


def test_generate_idea_headline_uses_fallback_when_model_json_invalid(monkeypatch):
    history = [
        {"role": "user", "content": "smartbookmarker extension to send selected text to google sheet tabs"},
        {"role": "gpt", "content": "what categories do you want?"},
    ]

    monkeypatch.setattr(openai_client, "get_client", lambda: _FakeClient("not a json payload"))

    headline, description = openai_client.generate_idea_headline(history)

    assert headline == "SmartBookmarker for Google Sheets"
    assert description


def test_generate_idea_headline_parses_fenced_json(monkeypatch):
    history = [{"role": "user", "content": "simple browser extension idea"}]
    content = """```json
{"headline": "Readable Idea Title", "description": "A short summary."}
```"""
    monkeypatch.setattr(openai_client, "get_client", lambda: _FakeClient(content))

    headline, description = openai_client.generate_idea_headline(history)

    assert headline == "Readable Idea Title"
    assert description == "A short summary."


def test_propose_idea_bootstrap_parses_payload(monkeypatch):
    payload = """```json
{"headline":"Smart Bookmarker for PM/BA","idea_id":"smart_bookmarker_pm_ba","assistant_message":"What user workflow should PM and BA prioritize first?"}
```"""
    monkeypatch.setattr(openai_client, "get_client", lambda: _FakeClient(payload))

    result = openai_client.propose_idea_bootstrap("smart bookmarker")

    assert result["headline"] == "Smart Bookmarker for PM/BA"
    assert result["idea_id"] == "smart_bookmarker_pm_ba"
    assert "PM and BA" in result["assistant_message"]


def test_propose_idea_bootstrap_fallback_on_invalid_json(monkeypatch):
    monkeypatch.setattr(openai_client, "get_client", lambda: _FakeClient("not json"))

    result = openai_client.propose_idea_bootstrap("audio summarizer")

    assert result["headline"]
    assert result["idea_id"] == "audio_summarizer"
    assert result["assistant_message"]
