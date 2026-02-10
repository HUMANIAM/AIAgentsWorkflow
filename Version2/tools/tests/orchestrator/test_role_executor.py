#!/usr/bin/env python3
"""Tests for role executor charter resolution."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from orchestrator import role_executor


def test_charter_mission_reads_from_version2_workflows():
    mission = role_executor._charter_mission("architect")
    assert "Produce minimal architecture aligned with ACs" in mission
