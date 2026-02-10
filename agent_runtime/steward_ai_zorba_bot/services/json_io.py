#!/usr/bin/env python3
"""Shared JSON read/write helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def load_json_dict(path: Path) -> Dict[str, Any]:
    """Load JSON file and enforce object root."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def save_json_dict(path: Path, data: Dict[str, Any]) -> None:
    """Atomically write JSON object to file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    tmp.replace(path)
