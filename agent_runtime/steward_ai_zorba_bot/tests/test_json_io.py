#!/usr/bin/env python3
"""Tests for shared JSON I/O helpers."""

import json
from pathlib import Path

import pytest

from services import json_io


def test_load_json_dict_rejects_non_object(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text("[1,2,3]\n", encoding="utf-8")
    with pytest.raises(ValueError):
        json_io.load_json_dict(path)


def test_save_json_dict_writes_object(tmp_path: Path):
    path = tmp_path / "good.json"
    payload = {"ok": True, "count": 2}
    json_io.save_json_dict(path, payload)

    parsed = json.loads(path.read_text(encoding="utf-8"))
    assert parsed == payload
