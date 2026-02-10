#!/usr/bin/env python3
"""Guardrails for Version2 tool-centric orchestrator inventory."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from orchestrator import validation


def test_version2_orchestrator_entrypoint_inventory():
    repo_root = Path(__file__).resolve().parents[4]

    assert (repo_root / "Version2" / "tools" / "src" / "orchestrator" / "main.py").exists()
    assert (repo_root / "Version2" / "tools" / "src" / "orchestrator" / "utils.py").exists()
    assert (repo_root / "Version2" / "tools" / "src" / "orchestrator" / "validation.py").exists()

    # Ensure deprecated Version2 wrappers are gone.
    assert not (repo_root / "Version2" / "orchestrator.py").exists()
    assert not (repo_root / "Version2" / "orchestrator_v2.py").exists()
    assert not (repo_root / "Version2" / "orchestrator_agent.py").exists()


def test_list_profiles_reads_yaml_files(tmp_path):
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "a.yaml").write_text("name: a\n", encoding="utf-8")
    (profiles / "b.yaml").write_text("name: b\n", encoding="utf-8")
    names = validation.list_profiles(profiles)
    assert names == ["a", "b"]


def test_load_json_requires_object(tmp_path):
    payload = tmp_path / "payload.json"
    payload.write_text("[1,2,3]\n", encoding="utf-8")
    with pytest.raises(ValueError):
        validation.load_json(payload)
