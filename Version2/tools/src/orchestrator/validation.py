#!/usr/bin/env python3
"""Validation and loading helpers for the Version2 orchestrator tool."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List

import yaml
from jsonschema import ValidationError, validate


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    tmp.replace(path)


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be object: {path}")
    return data


def load_schema(path: Path) -> Dict[str, Any]:
    return load_json(path)


def list_profiles(profiles_dir: Path) -> List[str]:
    if not profiles_dir.exists():
        return []
    names = [p.stem for p in profiles_dir.glob("*.yaml")]
    names.sort()
    return names


def load_and_validate_profile(
    profile_name: str,
    *,
    profiles_dir: Path,
    profile_schema_path: Path,
    error_cls: type[Exception],
    list_profiles_fn: Callable[[], List[str]],
) -> Dict[str, Any]:
    profile_path = profiles_dir / f"{profile_name}.yaml"
    if not profile_path.exists():
        available = ", ".join(list_profiles_fn()) or "(none)"
        raise error_cls(
            f"Unknown profile '{profile_name}'. Available profiles: {available}"
        )

    profile = load_yaml(profile_path)
    schema = load_schema(profile_schema_path)
    try:
        validate(instance=profile, schema=schema)
    except ValidationError as e:
        raise error_cls(
            f"Profile '{profile_name}' failed schema validation: {e.message}"
        ) from e
    return profile


def validate_status(status: Dict[str, Any], *, status_schema_path: Path, error_cls: type[Exception]) -> None:
    schema = load_schema(status_schema_path)
    try:
        validate(instance=status, schema=schema)
    except ValidationError as e:
        raise error_cls(f"status.json failed schema validation: {e.message}") from e
