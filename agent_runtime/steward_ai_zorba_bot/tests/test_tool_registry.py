#!/usr/bin/env python3
"""Tests for Version2 tools registry resolver."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from services import tool_registry


def test_resolve_tool_entrypoint_success(tmp_path, monkeypatch):
    tools_root = tmp_path / "tools"
    tools_root.mkdir(parents=True)
    src = tools_root / "src" / "orchestrator"
    src.mkdir(parents=True)
    entry = src / "main.py"
    entry.write_text("print('ok')\n", encoding="utf-8")

    registry = tools_root / "README.md"
    registry.write_text(
        "\n".join(
            [
                "## orchestrator",
                "- entrypoint: `src/orchestrator/main.py`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(tool_registry, "TOOLS_ROOT", tools_root)
    monkeypatch.setattr(tool_registry, "TOOLS_REGISTRY", registry)

    path, message = tool_registry.resolve_tool_entrypoint("orchestrator")
    assert message == "ok"
    assert path == entry.resolve()


def test_resolve_tool_entrypoint_missing_tool(tmp_path, monkeypatch):
    tools_root = tmp_path / "tools"
    tools_root.mkdir(parents=True)
    registry = tools_root / "README.md"
    registry.write_text("## something_else\n- entrypoint: `x.py`\n", encoding="utf-8")

    monkeypatch.setattr(tool_registry, "TOOLS_ROOT", tools_root)
    monkeypatch.setattr(tool_registry, "TOOLS_REGISTRY", registry)

    path, message = tool_registry.resolve_tool_entrypoint("orchestrator")
    assert path is None
    assert "entrypoint not found" in message.lower()
