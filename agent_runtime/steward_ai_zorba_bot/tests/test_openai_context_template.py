#!/usr/bin/env python3
"""Tests for strict context template contract generation."""

from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from services import openai_client


class _FakeClient:
    def __init__(self, content: str):
        self._content = content
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **_kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._content))]
        )


def _write_template(path: Path) -> None:
    path.write_text(
        "---\n"
        "plugin: idea\n"
        "version: 1\n"
        "owner: client\n"
        "last_updated: <YYYY-MM-DD>\n"
        "idea_id: <idea_id>\n"
        "---\n\n"
        "# What I want (client perspective)\n"
        "<fill>\n\n"
        "## The problem I have now:\n"
        "<fill>\n\n"
        "## What I need:\n"
        "- <fill>\n\n"
        "## What \"done\" means to me:\n"
        "- <fill>\n",
        encoding="utf-8",
    )


def test_generate_context_from_chat_injects_idea_id(monkeypatch, tmp_path):
    template = tmp_path / "context_template.md"
    _write_template(template)

    generated = """---
plugin: idea
version: 1
owner: client
last_updated: 2025-01-01
---

# What I want (client perspective)
Build a focused note workflow.

## The problem I have now:
Notes are scattered.

## What I need:
- Capture
- Categorize

## What \"done\" means to me:
- Reliable flow
"""

    monkeypatch.setattr(openai_client, "_context_template_path", lambda: template)
    monkeypatch.setattr(openai_client, "get_client", lambda: _FakeClient(generated))

    out = openai_client.generate_context_from_chat(
        [{"role": "user", "content": "build note workflow"}],
        idea_id="smart_notes",
    )

    assert out.startswith("---")
    assert "idea_id: smart_notes" in out
    assert "# What I want (client perspective)" in out
    assert "## The problem I have now:" in out
    assert "## What I need:" in out
    assert "## What \"done\" means to me:" in out


def test_generate_context_from_chat_fails_when_template_missing(monkeypatch, tmp_path):
    missing = tmp_path / "missing_template.md"
    monkeypatch.setattr(openai_client, "_context_template_path", lambda: missing)

    with pytest.raises(FileNotFoundError):
        openai_client.generate_context_from_chat(
            [{"role": "user", "content": "x"}],
            idea_id="idea_x",
        )


def test_apply_template_contract_rejects_missing_heading():
    template = """---
plugin: idea
version: 1
owner: client
last_updated: <YYYY-MM-DD>
idea_id: <idea_id>
---

# What I want (client perspective)

## The problem I have now:

## What I need:

## What \"done\" means to me:
"""

    bad_generated = """---
plugin: idea
version: 1
owner: client
last_updated: 2026-01-01
---

# What I want (client perspective)
text

## What I need:
- item
"""

    with pytest.raises(ValueError):
        openai_client._apply_template_contract(bad_generated, template, idea_id="idea_bad")
