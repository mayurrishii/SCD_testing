"""Cloud Clipboard — a single shared clipboard served over HTTPS.

Anyone who opens (or refreshes) the page sees the latest uploaded text.
Content persists in a JSON file so it survives restarts.
"""

import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_FILE = Path(os.environ.get("CLIPBOARD_FILE", str(BASE_DIR / "clipboard.json")))
MAX_TEXT_LEN = 1_000_000  # 1 MB sanity cap per upload

app = FastAPI(title="Cloud Clipboard")
_lock = threading.Lock()


class ClipboardUpdate(BaseModel):
    text: str = Field(..., max_length=MAX_TEXT_LEN)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load() -> dict:
    """Return the stored clipboard state: {"text": str, "updated_at": str|None}."""
    with _lock:
        if not DATA_FILE.exists():
            return {"text": "", "updated_at": None}
        try:
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            return {"text": data.get("text", ""), "updated_at": data.get("updated_at")}
        except (json.JSONDecodeError, OSError):
            return {"text": "", "updated_at": None}


def _save(text: str) -> dict:
    """Atomically persist new clipboard content and return the new state."""
    state = {"text": text, "updated_at": _now()}
    with _lock:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=DATA_FILE.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False)
            os.replace(tmp_path, DATA_FILE)
        except BaseException:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise
    return state


@app.get("/api/clipboard")
def get_clipboard():
    return _load()


@app.post("/api/clipboard")
def put_clipboard(update: ClipboardUpdate):
    return _save(update.text)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# API routes above take precedence; everything else falls through to static files
# (html=True serves index.html for "/").
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    ssl_kwargs = {}
    if os.environ.get("SSL_CERT_FILE") and os.environ.get("SSL_KEY_FILE"):
        ssl_kwargs = {
            "ssl_certfile": os.environ["SSL_CERT_FILE"],
            "ssl_keyfile": os.environ["SSL_KEY_FILE"],
        }
    uvicorn.run(app, host="0.0.0.0", port=port, **ssl_kwargs)
