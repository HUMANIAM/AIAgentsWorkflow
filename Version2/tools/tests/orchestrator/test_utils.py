#!/usr/bin/env python3
"""Tests for orchestrator utility helpers."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from orchestrator import utils


def test_slugify_and_artifact_slug_fallbacks():
    assert utils.slugify("SmartBookmarker: AI-Powered Bookmark Organizer") == "smartbookmarker_ai_powered_bookmark_organizer"
    status = {"active_idea_headline": "", "active_idea_id": "my_idea"}
    assert utils.artifact_slug_from_status(status) == "my_idea"


def test_parse_trigger_command_default_profile(monkeypatch):
    monkeypatch.delenv("ORCHESTRATOR_PROFILE", raising=False)
    profile = utils.parse_trigger_command(
        "/orchestrator",
        default_profile="default_fallback_profile",
        error_cls=RuntimeError,
    )
    assert profile == "default_fallback_profile"


def test_parse_invocation_requires_profile():
    with pytest.raises(RuntimeError):
        utils.parse_invocation(
            "/orchestrator",
            list_profiles_fn=lambda: ["default_fallback_profile"],
            error_cls=RuntimeError,
        )


def test_resolve_active_idea_id_from_context(tmp_path: Path):
    context = tmp_path / "context.md"
    context.write_text("---\nidea_id: idea_1\n---\n", encoding="utf-8")
    assert utils.resolve_active_idea_id(context, error_cls=RuntimeError) == "idea_1"


def test_resolve_trace_path_relative_to_runtime_root(tmp_path: Path):
    status = {"active_idea_headline": "Expense Tracker", "active_idea_id": "expense_tracker"}
    trace = utils.resolve_trace_path("logs/trace.csv", status, tmp_path)
    assert trace == (tmp_path / "logs" / "trace.csv").resolve()
