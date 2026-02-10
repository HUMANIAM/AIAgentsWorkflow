#!/usr/bin/env python3
"""Tests for activation ownership and execute gating."""

import json
from pathlib import Path
from types import SimpleNamespace
import sys
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from services import idea_handler


def _write_idea(path: Path, idea_id: str, owner: int, status: str) -> None:
    path.write_text(
        f"""## ID: {idea_id}
**Headline:** {idea_id}
**Owner User ID:** {owner}
**Created:** 2026-02-08T00:00:00Z
**Updated:** 2026-02-08T00:00:00Z
**Status:** {status}

### Chat History
**User:** test

### Runtime Adjustments
""",
        encoding="utf-8",
    )


def _write_context(path: Path, idea_id: Optional[str] = None) -> None:
    idea_line = f"idea_id: {idea_id}\n" if idea_id else ""
    path.write_text(
        "---\n"
        "plugin: idea\n"
        "version: 1\n"
        "owner: client\n"
        f"{idea_line}"
        "last_updated: 2026-02-08\n"
        "---\n\n"
        "# What I want (client perspective)\n"
        "test\n\n"
        "## The problem I have now:\n"
        "test\n\n"
        "## What I need:\n"
        "- test\n\n"
        "## What \"done\" means to me:\n"
        "- test\n",
        encoding="utf-8",
    )


def test_activate_overwrites_context_sets_activated_and_demotes_previous(monkeypatch, tmp_path):
    ideas_dir = tmp_path / "ideas"
    plugin_dir = tmp_path / "plugin"
    ideas_dir.mkdir(parents=True)
    plugin_dir.mkdir(parents=True)

    _write_idea(ideas_dir / "idea_old.md", "idea_old", owner=7, status="ACTIVATED")
    _write_idea(ideas_dir / "idea_new.md", "idea_new", owner=7, status="PLANNED")

    _write_context(plugin_dir / "context_idea_new.md", idea_id=None)
    (plugin_dir / "context.md").write_text("old-context", encoding="utf-8")

    monkeypatch.setattr(idea_handler, "IDEAS_DIR", ideas_dir)
    monkeypatch.setattr(idea_handler, "PLUGIN_DIR", plugin_dir)

    ok, message = idea_handler.activate_idea("idea_new", owner_user_id=7)

    assert ok is True
    assert "Activated context" in message

    active_context = (plugin_dir / "context.md").read_text(encoding="utf-8")
    assert "idea_id: idea_new" in active_context
    assert not list(plugin_dir.glob("context_backup_*"))

    assert idea_handler.get_idea("idea_new")["status"] == "ACTIVATED"
    assert idea_handler.get_idea("idea_old")["status"] == "PLANNED"


def test_execute_requires_activated(monkeypatch, tmp_path):
    ideas_dir = tmp_path / "ideas"
    plugin_dir = tmp_path / "plugin"
    ideas_dir.mkdir(parents=True)
    plugin_dir.mkdir(parents=True)

    _write_idea(ideas_dir / "idea_a.md", "idea_a", owner=11, status="PLANNED")
    _write_context(plugin_dir / "context.md", idea_id="idea_a")

    monkeypatch.setattr(idea_handler, "IDEAS_DIR", ideas_dir)
    monkeypatch.setattr(idea_handler, "PLUGIN_DIR", plugin_dir)

    called = {"subprocess": False}

    def _fake_run(*_args, **_kwargs):
        called["subprocess"] = True
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(idea_handler.subprocess, "run", _fake_run)

    ok, message = idea_handler.execute_idea("idea_a", owner_user_id=11)
    assert ok is False
    assert "ACTIVATED" in message
    assert called["subprocess"] is False


def test_execute_requires_context_idea_id_match(monkeypatch, tmp_path):
    ideas_dir = tmp_path / "ideas"
    plugin_dir = tmp_path / "plugin"
    ideas_dir.mkdir(parents=True)
    plugin_dir.mkdir(parents=True)

    _write_idea(ideas_dir / "idea_a.md", "idea_a", owner=11, status="ACTIVATED")
    _write_context(plugin_dir / "context.md", idea_id="idea_b")

    monkeypatch.setattr(idea_handler, "IDEAS_DIR", ideas_dir)
    monkeypatch.setattr(idea_handler, "PLUGIN_DIR", plugin_dir)

    ok, message = idea_handler.execute_idea("idea_a", owner_user_id=11)
    assert ok is False
    assert "belongs to `idea_b`" in message


def test_execute_success_sets_executing(monkeypatch, tmp_path):
    ideas_dir = tmp_path / "ideas"
    plugin_dir = tmp_path / "plugin"
    status_file = tmp_path / "status.json"
    ideas_dir.mkdir(parents=True)
    plugin_dir.mkdir(parents=True)

    _write_idea(ideas_dir / "idea_a.md", "idea_a", owner=11, status="ACTIVATED")
    _write_context(plugin_dir / "context.md", idea_id="idea_a")

    monkeypatch.setattr(idea_handler, "IDEAS_DIR", ideas_dir)
    monkeypatch.setattr(idea_handler, "PLUGIN_DIR", plugin_dir)
    monkeypatch.setattr(idea_handler, "STATUS_FILE", status_file)

    def _fake_run(*_args, **_kwargs):
        return SimpleNamespace(returncode=0, stdout="initialized", stderr="")

    monkeypatch.setattr(idea_handler.subprocess, "run", _fake_run)

    ok, message = idea_handler.execute_idea("idea_a", owner_user_id=11)
    assert ok is True
    assert "initialized" in message
    assert idea_handler.get_idea("idea_a")["status"] == "EXECUTING"


def test_execute_writes_active_idea_metadata_to_status(monkeypatch, tmp_path):
    ideas_dir = tmp_path / "ideas"
    plugin_dir = tmp_path / "plugin"
    status_file = tmp_path / "status.json"
    ideas_dir.mkdir(parents=True)
    plugin_dir.mkdir(parents=True)

    _write_idea(ideas_dir / "idea_a.md", "idea_a", owner=11, status="ACTIVATED")
    _write_context(plugin_dir / "context.md", idea_id="idea_a")

    monkeypatch.setattr(idea_handler, "IDEAS_DIR", ideas_dir)
    monkeypatch.setattr(idea_handler, "PLUGIN_DIR", plugin_dir)
    monkeypatch.setattr(idea_handler, "STATUS_FILE", status_file)

    def _fake_run(*_args, **_kwargs):
        status_file.write_text(
            '{"active_profile":"default_fallback_profile","current_phase":"requirements"}\n',
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="initialized", stderr="")

    monkeypatch.setattr(idea_handler.subprocess, "run", _fake_run)

    ok, _message = idea_handler.execute_idea("idea_a", owner_user_id=11)
    assert ok is True

    status = json.loads(status_file.read_text(encoding="utf-8"))
    assert status["active_idea_id"] == "idea_a"
    assert status["active_idea_headline"] == "idea_a"
    assert status["active_idea"]["id"] == "idea_a"
    assert status["active_idea"]["headline"] == "idea_a"
