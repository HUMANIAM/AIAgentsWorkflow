#!/usr/bin/env python3
"""Tests for context markdown normalization."""

from datetime import datetime, timezone

from services import openai_client


def test_normalize_context_strips_fence_and_rewrites_date():
    raw = """```markdown
---
plugin: SmartBookmarker
version: 1
owner: client
last_updated: 2023-10-05
---

# What I want
text
```"""
    out = openai_client._normalize_context_markdown(raw, plugin_name="smartbookmarker")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    assert "```" not in out
    assert "last_updated: 2023-10-05" not in out
    assert f"last_updated: {today}" in out
    assert out.startswith("---")


def test_normalize_context_adds_front_matter_if_missing():
    raw = "# What I want\ntext"
    out = openai_client._normalize_context_markdown(raw, plugin_name="idea_name")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    assert out.startswith("---")
    assert "plugin: idea_name" in out
    assert "version: 1" in out
    assert "owner: client" in out
    assert f"last_updated: {today}" in out
