#!/usr/bin/env python3
"""Tool registry resolver for Version2 tool entrypoints."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Tuple

from services.runtime_paths import resolve_project_root


PROJECT_ROOT = resolve_project_root()
TOOLS_ROOT = PROJECT_ROOT / "Version2" / "tools"
TOOLS_REGISTRY = TOOLS_ROOT / "README.md"


def _parse_entrypoint(tool_name: str, text: str) -> Optional[str]:
    section_pat = re.compile(rf"^##\s+{re.escape(tool_name)}\s*$", re.IGNORECASE | re.MULTILINE)
    match = section_pat.search(text)
    if not match:
        return None

    tail = text[match.end() :]
    next_section = re.search(r"^##\s+", tail, re.MULTILINE)
    block = tail[: next_section.start()] if next_section else tail

    for line in block.splitlines():
        stripped = line.strip()
        if not stripped.lower().startswith("- entrypoint:"):
            continue

        value = stripped.split(":", 1)[1].strip()
        if value.startswith("`") and value.endswith("`") and len(value) >= 2:
            value = value[1:-1].strip()
        return value or None
    return None


def resolve_tool_entrypoint(tool_name: str) -> Tuple[Optional[Path], str]:
    """
    Resolve tool entrypoint path from Version2 tools registry.

    Returns:
      (path, message). path is None on failure.
    """
    if not TOOLS_REGISTRY.exists():
        return None, f"Tool registry not found: {TOOLS_REGISTRY}"

    try:
        content = TOOLS_REGISTRY.read_text(encoding="utf-8")
    except Exception as exc:
        return None, f"Failed to read tool registry: {exc}"

    rel = _parse_entrypoint(tool_name, content)
    if not rel:
        return None, f"Tool `{tool_name}` entrypoint not found in {TOOLS_REGISTRY}"

    candidate = Path(rel)
    if not candidate.is_absolute():
        candidate = TOOLS_ROOT / candidate

    candidate = candidate.resolve()
    if not candidate.exists():
        return None, f"Tool `{tool_name}` path from registry does not exist: {candidate}"

    return candidate, "ok"
