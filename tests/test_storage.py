"""Unit tests for the JSON-file storage layer (_load / _save) and config."""

import importlib
import json
import os
import threading
from pathlib import Path
from unittest import mock

import main

# conftest points CLIPBOARD_FILE at a temp dir before main is imported
DATA_FILE = main.DATA_FILE
TEST_DIR = DATA_FILE.parent


def _reset(path: Path, content: str | None):
    """Write raw content to the data file (or delete it when None)."""
    if path.exists():
        path.unlink()
    if content is not None:
        path.write_text(content, encoding="utf-8")


# --- _load -----------------------------------------------------------------

def test_load_missing_file_returns_empty():
    _reset(DATA_FILE, None)
    assert main._load() == {"text": "", "updated_at": None}


def test_load_corrupt_json_returns_empty():
    _reset(DATA_FILE, "{this is not json!!")
    assert main._load() == {"text": "", "updated_at": None}


def test_load_json_without_expected_keys_uses_defaults():
    _reset(DATA_FILE, json.dumps({"something": "else"}))
    assert main._load() == {"text": "", "updated_at": None}


def test_load_returns_stored_state():
    state = {"text": "abc", "updated_at": "2026-01-01T00:00:00+00:00"}
    _reset(DATA_FILE, json.dumps(state))
    assert main._load() == state


# --- _save -----------------------------------------------------------------

def test_save_creates_missing_parent_dirs(tmp_path):
    target = tmp_path / "a" / "b" / "c" / "clip.json"
    old = main.DATA_FILE
    main.DATA_FILE = target
    try:
        state = main._save("nested")
    finally:
        main.DATA_FILE = old
    assert state["text"] == "nested"
    assert target.exists()


def test_save_writes_raw_utf8_not_escaped():
    _reset(DATA_FILE, None)
    main._save("\U0001F4CB")
    raw = DATA_FILE.read_text(encoding="utf-8")
    assert "\U0001F4CB" in raw          # stored as the literal char...
    assert "\\ud83d" not in raw         # ...not as \uXXXX escapes


def test_save_leaves_no_temp_files(tmp_path):
    target = tmp_path / "clip.json"
    old = main.DATA_FILE
    main.DATA_FILE = target
    try:
        for i in range(20):
            main._save(f"iteration {i}")
    finally:
        main.DATA_FILE = old
    assert not list(tmp_path.glob("*.tmp"))


def test_concurrent_saves_keep_file_valid():
    _reset(DATA_FILE, None)
    values = [f"thread-{t}-value-{i}" for t in range(8) for i in range(10)]
    chunks = [values[t::8] for t in range(8)]
    errors: list[Exception] = []

    def worker(subset):
        for v in subset:
            try:
                main._save(v)
            except Exception as e:  # surfaced by the assert below
                errors.append(e)

    threads = [threading.Thread(target=worker, args=(c,)) for c in chunks]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"{len(errors)} saves failed, e.g. {errors[0]!r}"
    on_disk = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    assert on_disk["text"] in values    # file intact, holds one of the writes
    assert not list(DATA_FILE.parent.glob("*.tmp"))


# --- configuration -----------------------------------------------------------

def test_data_file_follows_clipboard_file_env():
    """CLIPBOARD_FILE env var must be honoured (this is how Render points
    the app at its persistent disk)."""
    env_target = TEST_DIR / "env-driven.json"
    try:
        with mock.patch.dict(os.environ, {"CLIPBOARD_FILE": str(env_target)}):
            importlib.reload(main)
            assert main.DATA_FILE == env_target
    finally:
        # env is restored by patch.dict only after the with-block exits,
        # so the reload that resets DATA_FILE must happen here
        importlib.reload(main)

    assert main.DATA_FILE == DATA_FILE
