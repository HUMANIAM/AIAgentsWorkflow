#!/usr/bin/env python3
"""Shared runtime/path utilities for steward services."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path


def resolve_project_root() -> Path:
    """Resolve repository root by locating Version2 directory."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "Version2").exists():
            return parent
    return here.parent.parent.parent.parent


def resolve_agent_runtime_dir(project_root: Path) -> Path:
    """Resolve AGENT_RUNTIME_DIR relative to project root when needed."""
    raw = os.getenv("AGENT_RUNTIME_DIR", "agent_runtime").strip() or "agent_runtime"
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = project_root / candidate
    return candidate


def utc_now() -> str:
    """Return canonical UTC timestamp string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_today() -> str:
    """Return canonical UTC date string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def slugify(value: str, max_len: int = 0) -> str:
    """Normalize string into lowercase snake_case slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    if max_len > 0:
        return slug[:max_len]
    return slug
