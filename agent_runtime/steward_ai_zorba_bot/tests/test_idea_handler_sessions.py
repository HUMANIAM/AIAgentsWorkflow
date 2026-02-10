#!/usr/bin/env python3
"""Tests for restart-safe idea session restoration with per-idea files."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from services import idea_handler


def _write_idea(path: Path, idea_id: str, owner: int, created: str, status: str) -> None:
    path.write_text(
        f"""## ID: {idea_id}
**Headline:** Sample {idea_id}
**Owner User ID:** {owner}
**Created:** {created}
**Updated:** {created}
**Status:** {status}

### Chat History
**User:** test
**GPT:** test

### Runtime Adjustments
""",
        encoding="utf-8",
    )


def test_restore_active_sessions_with_owner_metadata(tmp_path, monkeypatch):
    ideas_dir = tmp_path / "ideas"
    ideas_dir.mkdir(parents=True)
    _write_idea(
        ideas_dir / "idea_owner_bound.md",
        idea_id="idea_owner_bound",
        owner=12345,
        created="2026-02-07T23:00:00Z",
        status="REFINING",
    )

    monkeypatch.setattr(idea_handler, "IDEAS_DIR", ideas_dir)
    idea_handler._active_sessions.clear()

    restored = idea_handler.restore_active_sessions()

    assert restored == {12345: "idea_owner_bound"}
    assert idea_handler.get_active_idea(12345) == "idea_owner_bound"


def test_restore_active_sessions_skips_non_refining(tmp_path, monkeypatch):
    ideas_dir = tmp_path / "ideas"
    ideas_dir.mkdir(parents=True)
    _write_idea(
        ideas_dir / "idea_refined.md",
        idea_id="idea_refined",
        owner=12345,
        created="2026-02-07T23:00:00Z",
        status="REFINED",
    )

    monkeypatch.setattr(idea_handler, "IDEAS_DIR", ideas_dir)
    idea_handler._active_sessions.clear()

    restored = idea_handler.restore_active_sessions()

    assert restored == {}


def test_restore_active_sessions_picks_latest_for_owner_and_normalizes_older(tmp_path, monkeypatch):
    ideas_dir = tmp_path / "ideas"
    ideas_dir.mkdir(parents=True)

    _write_idea(
        ideas_dir / "idea_old.md",
        idea_id="idea_old",
        owner=12345,
        created="2026-02-07T10:00:00Z",
        status="REFINING",
    )
    _write_idea(
        ideas_dir / "idea_new.md",
        idea_id="idea_new",
        owner=12345,
        created="2026-02-07T23:00:00Z",
        status="REFINING",
    )

    monkeypatch.setattr(idea_handler, "IDEAS_DIR", ideas_dir)
    idea_handler._active_sessions.clear()

    restored = idea_handler.restore_active_sessions()

    assert restored == {12345: "idea_new"}

    old_text = (ideas_dir / "idea_old.md").read_text(encoding="utf-8")
    assert "**Status:** REFINED" in old_text
