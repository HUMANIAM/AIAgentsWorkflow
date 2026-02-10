#!/usr/bin/env python3
"""Charter structure compliance tests for benchmark roles."""

from pathlib import Path

REQUIRED_SECTIONS = [
    "## Authority",
    "## Non-Authority",
    "## Required Inputs",
    "## Required Outputs",
    "## Quality Gates",
    "## Failure Policy",
    "## Handoff Packet Requirements",
    "## Definition of Done",
]

FILES = [
    "orchestrator.md",
    "human_engineer.md",
    "system_analyst.md",
    "requirements_reviewer.md",
    "architect.md",
    "architecture_reviewer.md",
    "devops_engineer.md",
    "backend_engineer.md",
    "frontend_engineer.md",
    "implementation_reviewer.md",
    "integration_tester.md",
    "qa_engineer.md",
    "security_engineer.md",
    "sre_engineer.md",
    "technical_writer.md",
    "release_reviewer.md",
    "release_manager.md",
    "ai_evaluator.md",
]


def test_benchmark_charters_have_required_sections():
    base = Path(__file__).resolve().parents[1] / ".windseruf" / "workflows"
    for name in FILES:
        text = (base / name).read_text(encoding="utf-8")
        for heading in REQUIRED_SECTIONS:
            assert heading in text, f"{name} missing section: {heading}"
