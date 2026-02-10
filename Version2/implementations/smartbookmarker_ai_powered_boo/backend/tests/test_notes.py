#!/usr/bin/env python3
from pathlib import Path
from backend.app import retrieve_notes, save_note


def test_save_and_retrieve_roundtrip(tmp_path: Path):
    store = tmp_path / "notes.json"
    sheet_dir = tmp_path / "mock_sheet"
    note = save_note(
        "AI bookmarks for reading",
        category="research",
        path=store,
        sheet_dir=sheet_dir,
    )
    assert note["category"] == "research"
    assert note["storage_mode"] in {"mock_sheet", "google_sheets"}

    notes = retrieve_notes(category="research", path=store)
    assert len(notes) == 1
    assert notes[0]["text"] == "AI bookmarks for reading"

    tab_file = sheet_dir / "research.md"
    assert tab_file.exists()
    content = tab_file.read_text(encoding="utf-8")
    assert "-----" in content
    assert "# " in content


def test_auto_category_and_headline(tmp_path: Path):
    store = tmp_path / "notes.json"
    sheet_dir = tmp_path / "mock_sheet"
    note = save_note(
        "This research paper explains bookmark ranking for AI tooling.",
        path=store,
        sheet_dir=sheet_dir,
    )
    assert note["category"] == "research"
    assert note["headline"] != "Untitled note"
