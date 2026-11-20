"""API-level tests: endpoints, validation, unicode, persistence, static page."""

import json
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

import main


# --- health ---------------------------------------------------------------

def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


# --- read -----------------------------------------------------------------

def test_get_empty_clipboard(client):
    res = client.get("/api/clipboard")
    assert res.status_code == 200
    assert res.json() == {"text": "", "updated_at": None}


def test_get_returns_stored_text(client):
    client.post("/api/clipboard", json={"text": "hello"})
    res = client.get("/api/clipboard")
    assert res.status_code == 200
    assert res.json()["text"] == "hello"


def test_updated_at_is_utc_iso8601(client):
    res = client.post("/api/clipboard", json={"text": "ts check"})
    assert res.status_code == 200
    stamp = res.json()["updated_at"]
    parsed = datetime.fromisoformat(stamp)
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timedelta(0)


# --- write ----------------------------------------------------------------

def test_post_returns_new_state(client):
    res = client.post("/api/clipboard", json={"text": "first"})
    assert res.status_code == 200
    body = res.json()
    assert body["text"] == "first"
    assert body["updated_at"]


def test_latest_upload_wins(client):
    client.post("/api/clipboard", json={"text": "old"})
    res = client.post("/api/clipboard", json={"text": "new"})
    assert res.status_code == 200
    assert res.json()["text"] == "new"
    assert client.get("/api/clipboard").json()["text"] == "new"


def test_post_empty_string_clears(client):
    client.post("/api/clipboard", json={"text": "some content"})
    res = client.post("/api/clipboard", json={"text": ""})
    assert res.status_code == 200
    assert res.json()["text"] == ""
    assert client.get("/api/clipboard").json()["text"] == ""


def test_post_multiline_whitespace_preserved(client):
    text = "line1\n  line2\ttabbed\n\nline5"
    res = client.post("/api/clipboard", json={"text": text})
    assert res.json()["text"] == text
    assert client.get("/api/clipboard").json()["text"] == text


# --- unicode ---------------------------------------------------------------

def test_post_emoji_roundtrip(client):
    text = "emoji test: \U0001F4CB\U0001F680"
    res = client.post("/api/clipboard", json={"text": text})
    assert res.json()["text"] == text
    assert client.get("/api/clipboard").json()["text"] == text


def test_post_cjk_roundtrip(client):
    text = "こんにちは世界 \U0001F30F"
    assert client.post("/api/clipboard", json={"text": text}).json()["text"] == text
    assert client.get("/api/clipboard").json()["text"] == text


# --- validation -------------------------------------------------------------

def test_post_missing_text_is_422(client):
    assert client.post("/api/clipboard", json={}).status_code == 422


def test_post_null_text_is_422(client):
    assert client.post("/api/clipboard", json={"text": None}).status_code == 422


def test_post_non_string_text_is_422(client):
    assert client.post("/api/clipboard", json={"text": 12345}).status_code == 422


def test_post_malformed_json_is_422(client):
    res = client.post(
        "/api/clipboard",
        content=b"{not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 422


def test_post_over_max_length_is_422(client):
    import main
    res = client.post("/api/clipboard", json={"text": "a" * (main.MAX_TEXT_LEN + 1)})
    assert res.status_code == 422


def test_post_exactly_max_length_ok(client):
    import main
    res = client.post("/api/clipboard", json={"text": "a" * main.MAX_TEXT_LEN})
    assert res.status_code == 200
    assert res.json()["text"] == "a" * main.MAX_TEXT_LEN


# --- persistence (simulated restart) ---------------------------------------

def test_content_persisted_to_disk(client, data_file):
    client.post("/api/clipboard", json={"text": "persist me"})
    on_disk = json.loads(data_file.read_text(encoding="utf-8"))
    assert on_disk["text"] == "persist me"
    assert on_disk["updated_at"]


def test_content_survives_restart(client):
    client.post("/api/clipboard", json={"text": "persist me"})
    fresh_client = TestClient(main.app)  # new client = simulated restart
    assert fresh_client.get("/api/clipboard").json()["text"] == "persist me"


# --- static page ------------------------------------------------------------

def test_index_page_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "Cloud Clipboard" in res.text
    assert "uploadBtn" in res.text


def test_unknown_route_404(client):
    assert client.get("/does-not-exist").status_code == 404
