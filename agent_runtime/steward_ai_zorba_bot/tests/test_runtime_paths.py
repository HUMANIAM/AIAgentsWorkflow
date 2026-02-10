#!/usr/bin/env python3
"""Tests for shared runtime path helpers."""

from pathlib import Path

from services import runtime_paths


def test_slugify_respects_max_len():
    value = "SmartBookmarker: AI Powered Bookmark Organizer"
    slug = runtime_paths.slugify(value, max_len=12)
    assert slug == "smartbookmar"


def test_resolve_agent_runtime_dir_relative(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("AGENT_RUNTIME_DIR", "Version2/agent_runtime")
    resolved = runtime_paths.resolve_agent_runtime_dir(tmp_path)
    assert resolved == tmp_path / "Version2" / "agent_runtime"


def test_resolve_agent_runtime_dir_absolute(monkeypatch, tmp_path: Path):
    absolute = tmp_path / "runtime_data"
    monkeypatch.setenv("AGENT_RUNTIME_DIR", str(absolute))
    resolved = runtime_paths.resolve_agent_runtime_dir(tmp_path)
    assert resolved == absolute
