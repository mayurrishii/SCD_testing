"""Shared fixtures.

Points CLIPBOARD_FILE at a throwaway directory *before* `main` is imported
(since main reads it at import time), and gives every test a clean data file.
"""

import os
import tempfile
from pathlib import Path

import pytest

TEST_DIR = Path(tempfile.mkdtemp(prefix="clipboard-tests-"))
DATA_FILE = TEST_DIR / "clipboard.json"
os.environ["CLIPBOARD_FILE"] = str(DATA_FILE)

import main  # noqa: E402  (must come after the env setup)
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client():
    """A fresh TestClient with an empty clipboard for each test."""
    if DATA_FILE.exists():
        DATA_FILE.unlink()
    yield TestClient(main.app)
    if DATA_FILE.exists():
        DATA_FILE.unlink()


@pytest.fixture()
def data_file():
    """Path of the backing JSON file, for file-level assertions."""
    return DATA_FILE
